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
from punch_exceptions import PunchExceptions

logger = logging.getLogger(__name__)

## Create all Elements First - We will arrange and re-size them later

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
        
        # Get camera settings from parent
        if hasattr(parent, 'settings'):
            self.settings = parent.settings
        else:
            self.settings = {}
        
        # Configure grid for centering
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Configure frame appearance
        self.configure(fg_color="transparent", corner_radius=5)  # Make frame transparent with rounded corners
        
        # Set fixed width and calculate height based on camera aspect ratio
        self.width = 410  # Fixed width
        camera_width = self.camera_service.settings['camera']['resolution']['width']
        camera_height = self.camera_service.settings['camera']['resolution']['height']
        aspect_ratio = camera_height / camera_width
        self.height = int(self.width * aspect_ratio)
        
        
        # Create frame for preview
        self.preview_frame = customtkinter.CTkFrame(
            self,
            width=410,
            height= int(410 * aspect_ratio),
            #fg_color='#2A2A2A',  # Match the dark theme background
            corner_radius=5
        )
        self.preview_frame.grid(row=0, column=0, padx=5, pady=0)
        self.preview_frame.grid_propagate(False)
        
        # Create canvas inside the frame
        self.canvas = customtkinter.CTkCanvas(
            self.preview_frame,
            width=410,
            height=int(410 * aspect_ratio),
            bg='#303030',  # Match the dark theme background
            highlightthickness=0  # Remove border
        )
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        
        self.current_image = None

    def start_preview(self):
        """Start camera preview"""
        if not self.camera_service.is_initialized:
            init_result = self.camera_service.initialize()
            
            if not init_result:
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
                # Resize frame to match canvas size
                frame = cv2.resize(frame, (410, 230), interpolation=cv2.INTER_AREA)
                
                # Convert frame to PhotoImage
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
                photo = ImageTk.PhotoImage(image=image)
                
                # Update canvas
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, image=photo, anchor="nw")
                self.current_image = photo  # Keep reference
            else:
                logger.error("CameraPreview: Failed to capture frame")
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
    def __init__(self, parent, settings: dict = None, settings_path: str = 'settings.json'):
        super().__init__(parent)
        self.settings = settings if settings is not None else self._load_settings(settings_path)
        
        # Initialize services
        logger.debug("TimeClockUI: Checking for parent camera service")
        
        # Use parent's camera service if available
        if hasattr(parent, 'camera_service') and parent.camera_service is not None:
            logger.debug("TimeClockUI: Using parent's camera service")
            self.camera_service = parent.camera_service
        else:
            logger.debug("TimeClockUI: Creating new camera service")
            self.camera_service = CameraService(settings_path)
        
        # Log camera settings
        logger.debug(f"TimeClockUI: Camera settings: {self.settings.get('camera', {})}")
        
        self.soap_client = SoapClient(settings_path)
        
        self.employee_id = customtkinter.StringVar()
        self.status_text = customtkinter.StringVar()
        self.status_text_es = customtkinter.StringVar()
        
        # Flag to track if admin panel is open
        self.admin_panel_open = False
        
        self.create_widgets()
        
        # Admin panel is handled by main window
        
        # Start camera preview
        logger.debug("TimeClockUI: Initializing camera service")
        init_result = self.camera_service.initialize()
        logger.debug(f"TimeClockUI: Camera initialization result: {init_result}")
        
        # Check if camera is in fallback mode
        if hasattr(self.camera_service, '_fallback_mode'):
            logger.debug(f"TimeClockUI: Camera fallback mode: {self.camera_service._fallback_mode}")
        
        logger.debug("TimeClockUI: Starting camera preview")
        self.camera_preview.start_preview()
        
        # Bind keyboard input
        self.bind('<Return>', self.process_punch)
        self.id_entry.bind('<Return>', self.process_punch)
        
        # Bind admin shortcut
        root = self.winfo_toplevel()
        root.bind(self.settings['ui']['adminShortcut'], self.show_admin_panel)
        
        # Initialize UI state after widget is fully created
        self.after(100, self.reset_ui)
        
        # Bind window activation event
        root.bind('<Map>', self.on_window_activate)
        root.bind('<FocusIn>', self.on_window_activate)
    def show_admin_panel(self, event=None):
        """Show the admin panel"""
        from admin_panel import show_admin_login, AdminPanel
        
        def on_login(success: bool):
            if success:
                # Set admin panel state
                self.admin_panel_open = True
                
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
                
                # Bind close event
                def on_admin_close():
                    self.admin_panel_open = False
                    admin_panel.destroy()
                
                admin_panel.protocol("WM_DELETE_WINDOW", on_admin_close)
        
        show_admin_login(self.winfo_toplevel(), on_login)

    def _load_settings(self, settings_path: str) -> dict:
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise

    def create_widgets(self):
        """Create all UI widgets"""
        # Logo is 361 x 156 px with 15px padding
        header_row = customtkinter.CTkFrame(
            self,
            height=187,
            fg_color="#212121"
        )
        
        # Create panel for left column
        left_column = customtkinter.CTkFrame (
            self,
            width = 364,
            height = 260,
            fg_color = "#404040",
            corner_radius = 8
        )
        left_column.grid_propagate(False)  # Prevent frame from shrinking
        
        # Create panel for right column
        right_column = customtkinter.CTkFrame (
            self,
            width = 420,
            height = 260,
            fg_color = "#303030",
            corner_radius = 8
        )
        right_column.grid_propagate(False)  # Prevent frame from shrinking
        right_column.grid_columnconfigure(0, weight=1)
        right_column.grid_rowconfigure(0, weight=1)
        
        # Create panel for bottom row
        bottom_row = customtkinter.CTkFrame (
            self,
            height = 153,
            fg_color = "#212121",
        )
        
        # Configure bottom_row grid for centering
        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_rowconfigure((0, 1), weight=1)
        
        # Configure grid weights for main frame
        self.grid_columnconfigure((0, 1), weight=0)  # Fixed width columns
        self.grid_rowconfigure((0, 1, 2), weight=1)  # Header, Clock/Camera, Status
        
        ########## Top Row - MSI logo spanning both columns
        header_row.grid(row=0, column=0, columnspan=2, pady=(15, 16), sticky='nsew')
        logo = customtkinter.CTkImage (
            light_image = Image.open("assets/logo.png"),
            dark_image = Image.open("assets/logo.png"),
            size = (361, 156)
        )
        # Configure header_row grid
        header_row.grid_columnconfigure(0, weight=1)
        header_row.grid_rowconfigure(0, weight=1)
        
        logo_image = customtkinter.CTkLabel(
            header_row,
            image=logo,
            text=''
        )
        logo_image.grid(row=0, column=0)
        
        ########## Left Column - Date and Time
        left_column.grid(row=1, column=0, sticky='nsew', padx=(5,3))
        left_column.grid_columnconfigure((0), weight=1)
        left_column.grid_rowconfigure((0,1,2), weight=0)
        
        # Date
        date_label = customtkinter.CTkLabel(
            left_column,
            text="",
            font=('IBM Plex Sans Medium', 24),
            text_color="#F0F0F0"
        )
        date_label.grid(row=0, column=0, sticky="nsew", pady=(20,0))
        
        # Update date
        def update_date():
            date_label.configure(text=datetime.now().strftime("%A, %B %d, %Y"))
            self.after(60000, update_date)  # Update every minute
        update_date()
        
        # Time
        self.timer_label = TimerLabel(left_column)
        self.timer_label.grid(row=1, column=0, pady=(0,30))
        
        # ID Entry Box
        self.id_entry = customtkinter.CTkEntry(
            left_column,
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
        self.id_entry.grid (row=2, column=0)
        
        ########## Right Column - Camera Preview
        right_column.grid(row=1, column=1, sticky="ns", padx=(3,5))
        # Create camera preview
        self.camera_preview = CameraPreview(right_column, self.camera_service)
        self.camera_preview.grid(row=0, column=0)
        
        ########## Bottom Row - Status Messages
        bottom_row.grid (row=2, column=0, columnspan=2, sticky="nsew")
        
        # Status labels
        self.status_label = customtkinter.CTkLabel(
            bottom_row,
            textvariable=self.status_text,
            font=('IBM Plex Sans Medium', 40,),
            text_color="#F0F0F0"
        )
        self.status_label_es = customtkinter.CTkLabel(
            bottom_row,
            textvariable=self.status_text_es,
            font=('IBM Plex Sans Medium', 40,),
            text_color="#F0F0F0"
        )
        self.status_label.grid(row=0, column=0, pady=(15,0))
        self.status_label_es.grid(row=1, column=0, pady=(0,20))
        
        # Bind Return key using correct customtkinter syntax
        self.id_entry.bind(sequence="<Return>", command=self.process_punch)

    def reset_ui(self):
        """Reset UI to initial state"""
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
            StatusColors.NORMAL
        )
        
        def process_in_thread():
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
                
                # Update UI in main thread
                def update_ui():
                    if response['offline']:
                        self.set_status(
                            "Punch saved offline",
                            "Datos guardados sin conexión",
                            StatusColors.INACTIVE
                        )
                        # Reset UI after standard delay
                        self.after(3000, self.reset_ui)
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
                        # Reset UI after standard delay
                        self.after(3000, self.reset_ui)
                    else:
                        # Check if there's a specific exception
                        if 'exception' in response and response['exception']:
                            exception_msg = PunchExceptions.get_message(response['exception'])
                            if exception_msg:
                                eng_msg, esp_msg, status_color = exception_msg
                                self.set_status(
                                    eng_msg,
                                    esp_msg,
                                    getattr(StatusColors, status_color)
                                )
                                # Reset UI after longer delay for exceptions (6 seconds)
                                self.after(6000, self.reset_ui)
                                return
                        
                        # Default error message if no specific exception is found
                        self.set_status(
                            "Punch failed - Please try again",
                            "Error - Por favor intente de nuevo",
                            StatusColors.ERROR
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
                        StatusColors.ERROR
                    )
                    # Reset UI after delay
                    self.after(3000, self.reset_ui)
                self.after(0, show_error)
        
        # Start processing in separate thread
        thread = threading.Thread(target=process_in_thread)
        thread.daemon = True  # Thread will be terminated when main program exits
        thread.start()
    
    def on_window_activate(self, event=None):
        """Handle window activation"""
        # Only set focus if no dialog/admin panel is active
        if not isinstance(self.winfo_toplevel().focus_get(), customtkinter.CTkToplevel):
            self.id_entry.focus_set()

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
