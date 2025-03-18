"""
Android-specific time clock UI implementation.
Uses KivyMD for Material Design components.
"""

import logging
from datetime import datetime
from functools import partial
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from msi_core.soap.client import SoapClient
from .admin_panel import show_admin_login, AdminPanel

logger = logging.getLogger(__name__)

# Load the KV file
Builder.load_file('platforms/android/ui/time_clock_ui.kv')

class TimerLabel(MDBoxLayout):
    """Widget that displays the current time"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_time()
    
    def update_time(self, *args):
        """Update the displayed time"""
        now = datetime.now()
        
        # Format hour without leading zero, minute and seconds with leading zero
        hour = str(int(now.strftime("%I")))  # Remove leading zero
        minute = now.strftime("%M")
        seconds = now.strftime("%S")
        ampm = now.strftime("%p")
        
        # Update time and AM/PM separately
        self.ids.time_label.text = f"{hour}:{minute}:{seconds}"
        self.ids.ampm_label.text = ampm
        
        # Schedule next update
        Clock.schedule_once(self.update_time, 1)

class TimeClockUI(MDBoxLayout):
    """Main time clock UI for Android"""
    
    # Status text properties
    status_text = StringProperty("")
    status_text_es = StringProperty("")
    status_color = StringProperty("#FFFFFF")
    
    def __init__(self, settings_manager, soap_client: SoapClient, **kwargs):
        """Initialize the time clock UI
        
        Args:
            settings_manager: Settings manager instance
            soap_client: SOAP client instance
        """
        super().__init__(**kwargs)
        self.settings_manager = settings_manager
        self.settings = settings_manager.get_settings()
        self.soap_client = soap_client
        
        # Initialize UI state
        Clock.schedule_once(self.reset_ui, 0.1)
        Clock.schedule_interval(self.update_date, 60)  # Update date every minute
        
        # Update date immediately
        self.update_date()

    def update_date(self, *args):
        """Update the displayed date"""
        self.ids.date_label.text = datetime.now().strftime("%A, %B %d, %Y")

    def reset_ui(self, *args):
        """Reset UI to initial state"""
        self.set_status("Please scan your ID", "Por favor pase su tarjeta", "#FFFFFF")
        self.ids.id_entry.text = ""
        self.ids.id_entry.focus = True

    def set_status(self, text: str, text_es: str, color: str):
        """Update status display
        
        Args:
            text: English status text
            text_es: Spanish status text
            color: Status text color
        """
        self.ids.status_label.text = text
        self.ids.status_label_es.text = text_es
        self.ids.status_label.text_color = color
        self.ids.status_label_es.text_color = color

    def process_punch(self, *args):
        """Process an employee punch"""
        employee_id = self.ids.id_entry.text.strip()
        if not employee_id:
            return
            
        # Clear entry field immediately
        self.ids.id_entry.text = ""
        
        # Set temporary status
        self.set_status(
            "Processing...",
            "Procesando...",
            "#FFFFFF"
        )
        
        def process_punch_result(response, *args):
            """Handle punch response in the main thread"""
            if response['offline']:
                self.set_status(
                    "Punch saved offline",
                    "Datos guardados sin conexión",
                    StatusColors.WARNING
                )
                Clock.schedule_once(self.reset_ui, 3)
            elif response['success']:
                if response['punchType'].lower() == 'checkin':
                    self.set_status(
                        f"Welcome {response['firstName']}!",
                        f"¡Bienvenido {response['firstName']}!",
                        StatusColors.SUCCESS
                    )
                else:
                    self.set_status(
                        f"Goodbye {response['firstName']}!",
                        f"¡Adiós {response['firstName']}!",
                        StatusColors.SUCCESS
                    )
                Clock.schedule_once(self.reset_ui, 3)
            else:
                # Check if there's a specific exception
                if 'exception' in response and response['exception']:
                    if response['exception'] == '1':
                        self.set_status(
                            "Shift not yet started",
                            "Turno no ha iniciado",
                            StatusColors.WARNING
                        )
                    elif response['exception'] == '2':
                        self.set_status(
                            "Not Authorized",
                            "No Autorizado",
                            StatusColors.ERROR
                        )
                    elif response['exception'] == '3':
                        self.set_status(
                            "Shift has finished",
                            "Turno ha finalizado",
                            StatusColors.WARNING
                        )
                    else:
                        self.set_status(
                            "Not Authorized",
                            "No Autorizado",
                            StatusColors.ERROR
                        )
                    Clock.schedule_once(self.reset_ui, 6)
                else:
                    self.set_status(
                        "Punch failed - Please try again",
                        "Error - Por favor intente de nuevo",
                        StatusColors.ERROR
                    )
                    Clock.schedule_once(self.reset_ui, 3)
        
        def process_error(error, *args):
            """Handle punch error in the main thread"""
            logger.error(f"Error processing punch: {error}")
            self.set_status(
                "System Error - Please try again",
                "Error del sistema - Por favor intente de nuevo",
                StatusColors.ERROR
            )
            Clock.schedule_once(self.reset_ui, 3)
        
        try:
            # Get current time for punch
            punch_time = datetime.now()
            
            # Record punch
            response = self.soap_client.record_punch(
                employee_id=employee_id,
                punch_time=punch_time
            )
            
            # Handle response in main thread
            Clock.schedule_once(partial(process_punch_result, response))
            
        except Exception as e:
            # Handle error in main thread
            Clock.schedule_once(partial(process_error, str(e)))

    def show_admin_panel(self):
        """Show the admin panel"""
        def on_login(success: bool):
            if success:
                # Create and show admin panel
                admin_panel = AdminPanel(
                    settings_manager=self.settings_manager,
                    name='admin'
                )
                self.parent.add_widget(admin_panel)
                self.parent.current = 'admin'
        
        show_admin_login(self, self.settings_manager, on_login)