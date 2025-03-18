"""
Windows-specific time clock UI implementation.
This version provides a simplified interface without camera functionality.
"""

import customtkinter
import logging
from datetime import datetime
from typing import Optional, Callable
import json
from msi_core.soap.client import SoapClient

logger = logging.getLogger(__name__)

class TimerLabel(customtkinter.CTkFrame):
    """Frame that displays date and time"""
    def __init__(self, parent):
        super().__init__(parent)
        
        self.configure(fg_color="transparent")
        
        # Configure grid for centering
        self.grid_columnconfigure((0, 1), weight=1)
        
        # Create time label with large, bold font
        self.time_label = customtkinter.CTkLabel(
            self,
            text="",
            font=('IBM Plex Sans Condensed Bold', 72),
            text_color="#F0F0F0"
        )
        self.time_label.grid(row=0, column=0)
        
        # Create AM/PM label
        self.ampm_label = customtkinter.CTkLabel(
            self,
            text="",
            font=('IBM Plex Sans Condensed Bold', 40),
            text_color="#F0F0F0"
        )
        self.ampm_label.grid(row=0, column=1, padx=(10, 0), pady=(25, 0))
        
        self.update_time()

    def update_time(self):
        """Update the displayed time"""
        now = datetime.now()
        
        # Format hour without leading zero, minute and seconds with leading zero
        hour = str(int(now.strftime("%I")))  # Remove leading zero
        minute = now.strftime("%M")
        seconds = now.strftime("%S")
        ampm = now.strftime("%p")
        
        # Update time and AM/PM separately
        self.time_label.configure(text=f"{hour}:{minute}:{seconds}")
        self.ampm_label.configure(text=ampm)
        
        self.after(1000, self.update_time)

class TimeClockUI(customtkinter.CTkFrame):
    """Main time clock UI for Windows"""
    
    def __init__(self, parent, settings_manager, soap_client: SoapClient):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.settings = settings_manager.get_settings()
        self.soap_client = soap_client
        
        self.employee_id = customtkinter.StringVar()
        self.status_text = customtkinter.StringVar()
        self.status_text_es = customtkinter.StringVar()
        
        self.create_widgets()
        
        # Bind keyboard input
        self.bind('<Return>', self.process_punch)
        self.id_entry.bind('<Return>', self.process_punch)
        
        # Initialize UI state
        self.after(100, self.reset_ui)

    def create_widgets(self):
        """Create all UI widgets"""
        # Configure grid weights for main frame
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)  # Header, Clock, Status
        
        ########## Top Row - MSI logo
        header_row = customtkinter.CTkFrame(
            self,
            height=187,
            fg_color="#212121"
        )
        header_row.grid(row=0, column=0, pady=(15, 16), sticky='nsew')
        
        # Configure header_row grid
        header_row.grid_columnconfigure(0, weight=1)
        header_row.grid_rowconfigure(0, weight=1)
        
        # Add logo
        logo = customtkinter.CTkImage(
            light_image=customtkinter.Image.open("assets/common/logo.png"),
            dark_image=customtkinter.Image.open("assets/common/logo.png"),
            size=(361, 156)
        )
        logo_image = customtkinter.CTkLabel(
            header_row,
            image=logo,
            text=''
        )
        logo_image.grid(row=0, column=0)
        
        ########## Middle Row - Date and Time
        middle_row = customtkinter.CTkFrame(
            self,
            fg_color="#404040",
            corner_radius=8
        )
        middle_row.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        middle_row.grid_columnconfigure(0, weight=1)
        middle_row.grid_rowconfigure((0, 1, 2), weight=0)
        
        # Date
        date_label = customtkinter.CTkLabel(
            middle_row,
            text="",
            font=('IBM Plex Sans Medium', 24),
            text_color="#F0F0F0"
        )
        date_label.grid(row=0, column=0, sticky="nsew", pady=(20, 0))
        
        # Update date
        def update_date():
            date_label.configure(text=datetime.now().strftime("%A, %B %d, %Y"))
            self.after(60000, update_date)  # Update every minute
        update_date()
        
        # Time
        self.timer_label = TimerLabel(middle_row)
        self.timer_label.grid(row=1, column=0, pady=(0, 30))
        
        # ID Entry Box
        self.id_entry = customtkinter.CTkEntry(
            middle_row,
            textvariable=self.employee_id,
            font=('IBM Plex Sans Medium', 24),
            justify="center",
            width=292,
            height=53,
            border_color="#A4D233",
            border_width=4,
            fg_color="#212121",
            text_color="#F0F0F0"
        )
        self.id_entry.grid(row=2, column=0, pady=(0, 20))
        
        ########## Bottom Row - Status Messages
        bottom_row = customtkinter.CTkFrame(
            self,
            height=153,
            fg_color="#212121"
        )
        bottom_row.grid(row=2, column=0, sticky="nsew")
        
        # Configure bottom_row grid for centering
        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_rowconfigure((0, 1), weight=1)
        
        # Status labels
        self.status_label = customtkinter.CTkLabel(
            bottom_row,
            textvariable=self.status_text,
            font=('IBM Plex Sans Medium', 40),
            text_color="#F0F0F0"
        )
        self.status_label_es = customtkinter.CTkLabel(
            bottom_row,
            textvariable=self.status_text_es,
            font=('IBM Plex Sans Medium', 40),
            text_color="#F0F0F0"
        )
        self.status_label.grid(row=0, column=0, pady=(15, 0))
        self.status_label_es.grid(row=1, column=0, pady=(0, 20))

    def reset_ui(self):
        """Reset UI to initial state"""
        self.set_status("Please scan your ID", "Por favor pase su tarjeta", "#FFFFFF")
        self.after(100, lambda: self.id_entry.focus_set())

    def set_status(self, text: str, text_es: str, color: str):
        """Update status display"""
        self.status_text.set(text)
        self.status_text_es.set(text_es)
        self.status_label.configure(text_color=color)
        self.status_label_es.configure(text_color=color)
        self.update()  # Force update of the UI

    def process_punch(self, event=None):
        """Process an employee punch"""
        import threading
        
        employee_id = self.employee_id.get().strip()
        if not employee_id:
            return
            
        # Clear entry field immediately
        self.employee_id.set("")
        self.update()  # Force update to show cleared entry
        
        # Set temporary status
        self.set_status(
            "Processing...",
            "Procesando...",
            "#FFFFFF"
        )
        
        def process_in_thread():
            try:
                # Get current time for punch
                punch_time = datetime.now()
                
                # Record punch
                response = self.soap_client.record_punch(
                    employee_id=employee_id,
                    punch_time=punch_time
                )
                
                # Update UI in main thread
                def update_ui():
                    if response['offline']:
                        self.set_status(
                            "Punch saved offline",
                            "Datos guardados sin conexión",
                            "#F39C12"  # Warning color
                        )
                        # Reset UI after standard delay
                        self.after(3000, self.reset_ui)
                    elif response['success']:
                        if response['punchType'].lower() == 'checkin':
                            self.set_status(
                                f"Welcome {response['firstName']}!",
                                f"¡Bienvenido {response['firstName']}!",
                                "#34C759"  # Success color
                            )
                        else:
                            self.set_status(
                                f"Goodbye {response['firstName']}!",
                                f"¡Adiós {response['firstName']}!",
                                "#34C759"  # Success color
                            )
                        # Reset UI after standard delay
                        self.after(3000, self.reset_ui)
                    else:
                        # Check if there's a specific exception
                        if 'exception' in response and response['exception']:
                            if response['exception'] == '1':
                                self.set_status(
                                    "Shift not yet started",
                                    "Turno no ha iniciado",
                                    "#F39C12"  # Warning color
                                )
                            elif response['exception'] == '2':
                                self.set_status(
                                    "Not Authorized",
                                    "No Autorizado",
                                    "#FF3B30"  # Error color
                                )
                            elif response['exception'] == '3':
                                self.set_status(
                                    "Shift has finished",
                                    "Turno ha finalizado",
                                    "#F39C12"  # Warning color
                                )
                            else:
                                self.set_status(
                                    "Not Authorized",
                                    "No Autorizado",
                                    "#FF3B30"  # Error color
                                )
                            # Reset UI after longer delay for exceptions
                            self.after(6000, self.reset_ui)
                            return
                        
                        # Default error message if no specific exception is found
                        self.set_status(
                            "Punch failed - Please try again",
                            "Error - Por favor intente de nuevo",
                            "#FF3B30"  # Error color
                        )
                        # Reset UI after standard delay
                        self.after(3000, self.reset_ui)
                
                # Schedule UI update in main thread
                self.after(0, update_ui)
                
            except Exception as e:
                logger.error(f"Error processing punch: {e}")
                def show_error():
                    self.set_status(
                        "System Error - Please try again",
                        "Error del sistema - Por favor intente de nuevo",
                        "#FF3B30"  # Error color
                    )
                    # Reset UI after delay
                    self.after(3000, self.reset_ui)
                self.after(0, show_error)
        
        # Start processing in separate thread
        thread = threading.Thread(target=process_in_thread)
        thread.daemon = True  # Thread will be terminated when main program exits
        thread.start()