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
    def __init__(self, parent, scaling_factor: float, scaled_fonts: dict):
        super().__init__(parent)
        
        self.scaling_factor = scaling_factor
        self.scaled_fonts = scaled_fonts
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        
        # Create a frame to hold time and AM/PM horizontally
        time_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        time_frame.grid(row=0, column=0, sticky="ew")
        
        # Configure time frame grid - center the time display
        time_frame.grid_columnconfigure((0, 2), weight=1)  # Equal weight to columns before and after
        
        # Create time label with larger, bold font
        self.time_label = customtkinter.CTkLabel(
            time_frame,
            text="",
            font=self.scaled_fonts['clock']
        )
        self.time_label.grid(row=0, column=1, padx=(0, 10))
        
        # Create smaller AM/PM label
        self.ampm_label = customtkinter.CTkLabel(
            time_frame,
            text="",
            font=self.scaled_fonts['ampm'],
            anchor="s"  # Align to bottom
        )
        # Scale the padding for AM/PM alignment
        ampm_padding = int(35 * self.scaling_factor)
        self.ampm_label.grid(row=0, column=2, sticky="w", pady=(ampm_padding, 0))
        
        self.update_time()

    def update_time(self):
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

class CameraPreview(customtkinter.CTkFrame):
    """Frame that shows camera preview"""
    def __init__(self, parent, camera_service: CameraService):
        super().__init__(parent)
        self.camera_service = camera_service
        self.preview_active = False
        
        # Get scaling factor and fonts from parent's settings
        if hasattr(parent, 'settings'):
            self.scaling_factor = parent.settings['ui'].get('scaling_factor', 1.0)
            self.scaled_fonts = parent.scaled_fonts
        else:
            self.scaling_factor = 1.0
            self.scaled_fonts = {}
        
        # Configure grid for centering
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Get scaled dimensions
        self.width = self.camera_service.settings['camera']['resolution']['width']
        self.height = self.camera_service.settings['camera']['resolution']['height']
        
        # Create canvas for preview with transparent background
        self.canvas = customtkinter.CTkCanvas(
            self,
            width=self.width,
            height=self.height,
            bg='#2A2A2A',  # Match the dark theme background
            highlightthickness=0  # Remove border
        )
        self.canvas.grid(row=0, column=0)
        
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
                    font=('Roboto', int(14 * self.scaling_factor)),
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
                font=('Roboto', int(14 * self.scaling_factor)),
                justify="center"
            )
        
        if self.preview_active:
            self.after(33, self.update_preview)  # ~30 FPS

class TimeClockUI(customtkinter.CTkFrame):
    def __init__(self, parent, settings: dict = None, settings_path: str = 'settings.json'):
        super().__init__(parent)
        self.settings = settings if settings is not None else self._load_settings(settings_path)
        
        # Get scaling factor
        self.scaling_factor = self.settings['ui'].get('scaling_factor', 1.0)
        
        # Initialize services
        self.camera_service = CameraService(settings_path)
        self.soap_client = SoapClient(settings_path)
        
        self.employee_id = customtkinter.StringVar()
        self.status_text = customtkinter.StringVar()
        self.status_text_es = customtkinter.StringVar()
        
        # Scale font sizes
        self.scaled_fonts = {
            'clock': ('Roboto', int(72 * self.scaling_factor), 'bold'),
            'ampm': ('Roboto', int(36 * self.scaling_factor), 'bold'),
            'date': ('Roboto', int(24 * self.scaling_factor)),
            'status': ('Roboto', int(24 * self.scaling_factor)),
            'entry': ('Open Sans', int(14 * self.scaling_factor), 'bold')
        }
        
        self.create_widgets()
        
        # Start camera preview
        self.camera_service.initialize()
        self.camera_preview.start_preview()
        
        # Bind keyboard input
        self.bind('<Return>', self.process_punch)
        self.id_entry.bind('<Return>', self.process_punch)
        # Admin shortcut is bound in main.py
        
        # Initialize UI state after widget is fully created
        self.after(100, self.reset_ui)

    def show_admin_panel(self, event=None):
        """Show the admin panel"""
        from admin_panel import show_admin_login, AdminPanel
        
        def on_login(success: bool):
            if success:
                # Create admin panel window
                admin_panel = AdminPanel(self.winfo_toplevel())
                
                # Center and show the window
                admin_panel.update_idletasks()
                screen_width = admin_panel.winfo_screenwidth()
                screen_height = admin_panel.winfo_screenheight()
                x = (screen_width - admin_panel.winfo_width()) // 2
                y = (screen_height - admin_panel.winfo_height()) // 2
                admin_panel.geometry(f"+{x}+{y}")
                admin_panel.lift()
                admin_panel.focus_force()
        
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
        self.grid_rowconfigure((0, 1, 2), weight=0)  # No expansion by default
        
        # Top row (20% height) - Green header with logo and date
        header_frame = customtkinter.CTkFrame(self, fg_color="#A4D233", height=int(self.winfo_screenheight() * 0.2))
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)  # Force height
        header_frame.grid_columnconfigure((0, 1), weight=1)  # Equal columns
        
        # Calculate logo size based on header height
        header_height = int(self.winfo_screenheight() * 0.2)
        logo_height = int(header_height * 0.7)  # Logo takes 70% of header height
        logo_width = int(logo_height * 2.5)  # Maintain aspect ratio
        
        # Load and display logo
        try:
            logo_image = customtkinter.CTkImage(
                light_image=Image.open("assets/logo-white.png"),
                dark_image=Image.open("assets/logo-white.png"),
                size=(logo_width, logo_height)
            )
            logo_label = customtkinter.CTkLabel(
                header_frame,
                image=logo_image,
                text=""
            )
            logo_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        except Exception as e:
            logger.error(f"Failed to load logo: {e}")
        
        # Date display (right side of header)
        date_label = customtkinter.CTkLabel(
            header_frame,
            text="",
            font=('Roboto', int(32 * self.scaling_factor), 'bold'),  # Larger, bold font
            text_color="#FFFFFF"
        )
        date_label.grid(row=0, column=1, padx=40, pady=10, sticky="e")
        
        # Update date
        def update_date():
            date_label.configure(text=datetime.now().strftime("%A, %B %d, %Y"))
            self.after(60000, update_date)  # Update every minute
        update_date()
        
        # Middle row (60% height) - Clock/Entry and Camera
        middle_frame = customtkinter.CTkFrame(self, height=int(self.winfo_screenheight() * 0.6))
        middle_frame.grid(row=1, column=0, sticky="ew")
        middle_frame.grid_propagate(False)  # Force height
        middle_frame.grid_columnconfigure((0, 1), weight=1)  # Equal columns
        
        # Left column - Clock and Entry
        left_column = customtkinter.CTkFrame(middle_frame, fg_color="transparent")
        left_column.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        left_column.grid_columnconfigure(0, weight=1)
        
        # Clock display
        self.timer_label = TimerLabel(left_column, self.scaling_factor, self.scaled_fonts)
        self.timer_label.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # ID Entry
        entry_width = int(200 * self.scaling_factor)
        self.id_entry = customtkinter.CTkEntry(
            left_column,
            textvariable=self.employee_id,
            font=self.scaled_fonts['entry'],
            justify="center",
            width=entry_width
        )
        self.id_entry.grid(row=1, column=0, pady=20)
        
        # Right column - Camera Preview with transparent background
        camera_width = int(self.camera_service.settings['camera']['resolution']['width'] * self.scaling_factor)
        camera_height = int(self.camera_service.settings['camera']['resolution']['height'] * self.scaling_factor)
        self.camera_service.settings['camera']['resolution']['width'] = camera_width
        self.camera_service.settings['camera']['resolution']['height'] = camera_height
        
        camera_frame = customtkinter.CTkFrame(middle_frame, fg_color="transparent")
        camera_frame.grid(row=0, column=1, sticky="nsew")
        camera_frame.grid_columnconfigure(0, weight=1)
        camera_frame.grid_rowconfigure(0, weight=1)
        
        self.camera_preview = CameraPreview(camera_frame, self.camera_service)
        self.camera_preview.configure(fg_color="transparent")
        self.camera_preview.grid(row=0, column=0)
        
        # Bottom row (20% height) - Status Messages
        bottom_frame = customtkinter.CTkFrame(self, height=int(self.winfo_screenheight() * 0.2))
        bottom_frame.grid(row=2, column=0, sticky="ew")
        bottom_frame.grid_propagate(False)  # Force height
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        # Status labels container for closer spacing
        status_container = customtkinter.CTkFrame(bottom_frame, fg_color="transparent")
        status_container.grid(row=0, column=0)
        
        # Larger status labels with less spacing
        self.status_label = customtkinter.CTkLabel(
            status_container,
            textvariable=self.status_text,
            font=('Roboto', int(36 * self.scaling_factor), 'bold')  # Larger font
        )
        self.status_label.grid(row=0, column=0, pady=(0, 5))  # Reduced spacing
        
        self.status_label_es = customtkinter.CTkLabel(
            status_container,
            textvariable=self.status_text_es,
            font=('Roboto', int(36 * self.scaling_factor), 'bold')  # Larger font
        )
        self.status_label_es.grid(row=1, column=0)
        
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
    
    # Configure grid weights for root window
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    
    app = TimeClockUI(root)
    app.grid(row=0, column=0, sticky="nsew")
    
    # Configure for fullscreen
    root.attributes('-fullscreen', True)
    root.mainloop()
