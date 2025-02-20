import customtkinter
import cv2
from PIL import Image, ImageTk
import logging
from datetime import datetime
from typing import Optional, Callable
import json
from camera_service import CameraService
from soap_client import SoapClient
from ui_theme import StatusColors

logger = logging.getLogger(__name__)

class TimerLabel(customtkinter.CTkFrame):
    """Frame that displays date and time"""
    def __init__(self, parent):
        super().__init__(parent)
        
        # Create date label
        self.date_label = customtkinter.CTkLabel(
            self,
            text="",
            font=('Roboto', 24)
        )
        self.date_label.pack(pady=(0, 10))
        
        # Create a frame to hold time and AM/PM horizontally
        time_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        time_frame.pack(pady=(0, 10))
        
        # Create time label with larger, bold font
        self.time_label = customtkinter.CTkLabel(
            time_frame,
            text="",
            font=('Roboto', 72, 'bold')
        )
        self.time_label.pack(side="left", padx=(0, 10))
        
        # Create smaller AM/PM label
        self.ampm_label = customtkinter.CTkLabel(
            time_frame,
            text="",
            font=('Roboto', 36, 'bold'),
            anchor="s"  # Align to bottom
        )
        self.ampm_label.pack(side="left", padx=(0, 0), pady=(35, 0))  # Add top padding to align with bottom of clock
        
        self.update_time()

    def update_time(self):
        now = datetime.now()
        
        # Update date (Day of Week, Month Date, Year)
        date_str = now.strftime("%A, %B %d, %Y")
        self.date_label.configure(text=date_str)
        
        # Format hour without leading zero, minute and seconds with leading zero
        hour = str(int(now.strftime("%I")))  # Remove leading zero
        minute = now.strftime("%M")
        seconds = now.strftime("%S")
        ampm = now.strftime("%p")
        
        # Update time and AM/PM separately
        self.time_label.configure(text=f"{hour}:{minute}:{seconds}")
        self.ampm_label.configure(text=ampm)
        
        self.after(1000, self.update_time)

class CameraPreview(customtkinter.CTkFrame):
    """Frame that shows camera preview"""
    def __init__(self, parent, camera_service: CameraService):
        super().__init__(parent)
        self.camera_service = camera_service
        self.preview_active = False
        
        # Create canvas for preview
        self.canvas = customtkinter.CTkCanvas(
            self,
            width=self.camera_service.settings['camera']['resolution']['width'],
            height=self.camera_service.settings['camera']['resolution']['height']
        )
        self.canvas.pack()
        
        self.current_image = None

    def start_preview(self):
        """Start camera preview"""
        if not self.camera_service.is_initialized:
            if not self.camera_service.initialize():
                logger.error("Failed to initialize camera for preview")
                return
        self.preview_active = True
        self.update_preview()

    def stop_preview(self):
        """Stop camera preview"""
        self.preview_active = False
        if self.current_image:
            self.canvas.delete("all")
            self.current_image = None
        if self.camera_service.is_initialized:
            self.camera_service.cleanup()

    def update_preview(self):
        """Update preview frame"""
        if not self.preview_active:
            return

        try:
            result = self.camera_service.capture_frame()
            if result:
                frame, _ = result
                # Convert frame to PhotoImage
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
                photo = ImageTk.PhotoImage(image=image)
                
                # Update canvas
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, image=photo, anchor="nw")
                self.current_image = photo  # Keep reference
            else:
                # Show error message if frame capture failed
                self.canvas.delete("all")
                self.canvas.create_text(
                    self.canvas.winfo_width() // 2,
                    self.canvas.winfo_height() // 2,
                    text="Camera Error\nNo image available",
                    fill=StatusColors.ERROR,
                    font=('Roboto', 14),
                    justify="center"
                )
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text=f"Camera Error\n{str(e)}",
                fill=StatusColors.ERROR,
                font=('Roboto', 14),
                justify="center"
            )
        
        if self.preview_active:
            self.after(33, self.update_preview)  # ~30 FPS

class TimeClockUI(customtkinter.CTkFrame):
    def __init__(self, parent, settings_path: str = 'settings.json'):
        super().__init__(parent)
        self.settings = self._load_settings(settings_path)
        
        # Initialize services
        self.camera_service = CameraService(settings_path)
        self.soap_client = SoapClient(settings_path)
        
        self.employee_id = customtkinter.StringVar()
        self.status_text = customtkinter.StringVar()
        self.status_text_es = customtkinter.StringVar()
        
        self.create_widgets()
        
        # Start camera preview
        self.camera_service.initialize()
        self.camera_preview.start_preview()
        
        # Bind keyboard input using regular bind
        self.bind('<Return>', self.process_punch)
        self.id_entry.bind('<Return>', self.process_punch)
        parent.bind(self.settings['ui']['adminShortcut'], self.show_admin_panel)
        
        # Initialize UI state after widget is fully created
        self.after(100, self.reset_ui)

    def show_admin_panel(self, event=None):
        """Show the admin panel"""
        from admin_panel import show_admin_login, AdminPanel
        
        def on_login(success: bool):
            if success:
                AdminPanel(self.winfo_toplevel())
        
        show_admin_login(self.winfo_toplevel(), on_login)

    def _load_settings(self, settings_path: str) -> dict:
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise

    def create_widgets(self):
        # Configure grid weights for main frame
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Make camera row expandable
        
        # Main container with padding
        main_container = customtkinter.CTkFrame(self)
        main_container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # Configure grid weights for main container
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(2, weight=1)  # Camera row
        
        # Top section with time
        self.timer_label = TimerLabel(main_container)
        self.timer_label.grid(row=0, column=0, pady=(0, 20), sticky="ew")
        
        # Status labels (English and Spanish)
        status_frame = customtkinter.CTkFrame(main_container, fg_color="transparent")
        status_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = customtkinter.CTkLabel(
            status_frame,
            textvariable=self.status_text,
            font=('Roboto', 24)
        )
        self.status_label.grid(row=0, column=0, sticky="ew")
        
        self.status_label_es = customtkinter.CTkLabel(
            status_frame,
            textvariable=self.status_text_es,
            font=('Roboto', 24)
        )
        self.status_label_es.grid(row=1, column=0, sticky="ew")
        
        # Camera preview
        self.camera_preview = CameraPreview(main_container, self.camera_service)
        self.camera_preview.grid(row=2, column=0, sticky="nsew", pady=10)
        
        # Bottom section with ID entry
        bottom_frame = customtkinter.CTkFrame(main_container, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, sticky="ew", pady=(20, 0))
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        # Hidden entry for ID
        self.id_entry = customtkinter.CTkEntry(
            bottom_frame,
            textvariable=self.employee_id,
            font=('Open Sans', 14, 'bold'),
            justify="center",
            width=200  # Set fixed width for better centering
        )
        self.id_entry.grid(row=0, column=0)
        
        # Bind Return key using correct customtkinter syntax
        self.id_entry.bind(sequence="<Return>", command=self.process_punch)

    def reset_ui(self):
        """Reset UI to initial state"""
        self.employee_id.set("")
        self.set_status("Please scan your ID", "Por favor pase su tarjeta", StatusColors.NORMAL)
        # Schedule focus_set after widget is fully rendered
        self.after(100, lambda: self.id_entry.focus_set())

    def set_status(self, text: str, text_es: str, color: str):
        """Update status display"""
        self.status_text.set(text)
        self.status_text_es.set(text_es)
        self.status_label.configure(text_color=color)
        self.status_label_es.configure(text_color=color)
        self.update()  # Force update of the UI

    def on_key_press(self, event):
        """Handle keyboard input"""
        if event.char.isprintable():
            # Append the character to the entry if it's printable
            current = self.employee_id.get()
            self.employee_id.set(current + event.char)

    def process_punch(self, event=None):
        """Process an employee punch"""
        employee_id = self.employee_id.get().strip()
        if not employee_id:
            return
        
        try:
            # Get current time once to use for both punch and photo
            punch_time = datetime.now()
            
            # Capture photo first with the timestamp
            photo_data = self.camera_service.capture_photo(employee_id, punch_time)
            
            # Record punch with same timestamp
            response = self.soap_client.record_punch(
                employee_id=employee_id,
                punch_time=punch_time
            )
            
            # If punch was successful, upload the photo with same timestamp
            if response['success'] and photo_data:
                self.soap_client._upload_image(employee_id, photo_data, punch_time)
            
            # Handle response
            if response['offline']:
                self.set_status(
                    "Punch saved offline",
                    "Datos guardados sin conexión",
                    StatusColors.INACTIVE
                )
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
            else:
                self.set_status(
                    "Punch failed - Please try again",
                    "Error - Por favor intente de nuevo",
                    StatusColors.ERROR
                )
            
        except Exception as e:
            logger.error(f"Error processing punch: {e}")
            self.set_status(
                "System Error - Please try again",
                "Error del sistema - Por favor intente de nuevo",
                StatusColors.ERROR
            )
        
        finally:
            # Clean up
            self.employee_id.set("")
            
            # Reset UI and ensure focus after delay
            def reset_with_focus():
                self.reset_ui()
                self.after(100, lambda: self.id_entry.focus_set())
            self.after(3000, reset_with_focus)

if __name__ == "__main__":
    # Test UI
    root = customtkinter.CTk()
    root.title("Time Clock")
    
    app = TimeClockUI(root)
    app.pack(fill="both", expand=True)
    
    # Configure for fullscreen
    root.attributes('-fullscreen', True)
    root.mainloop()
