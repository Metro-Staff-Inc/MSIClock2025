import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import logging
from datetime import datetime
from typing import Optional, Callable
import json
from camera_service import CameraService
from soap_client import SoapClient
from ui_constants import Colors

logger = logging.getLogger(__name__)

class TimerLabel(ttk.Label):
    """Label that displays current time"""
    def __init__(self, parent):
        super().__init__(parent, font=('Arial', 36), foreground=Colors.BLACK)
        self.update_time()

    def update_time(self):
        current_time = datetime.now().strftime("%I:%M:%S %p")
        self.configure(text=current_time)
        self.after(1000, self.update_time)

class CameraPreview(ttk.Frame):
    """Frame that shows camera preview"""
    def __init__(self, parent, camera_service: CameraService):
        super().__init__(parent)
        self.camera_service = camera_service
        self.preview_active = False
        
        # Create canvas for preview
        self.canvas = tk.Canvas(
            self,
            width=self.camera_service.settings['camera']['resolution']['width'],
            height=self.camera_service.settings['camera']['resolution']['height'],
            background=Colors.WHITE
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
                self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                self.current_image = photo  # Keep reference
            else:
                # Show error message if frame capture failed
                self.canvas.delete("all")
                self.canvas.create_text(
                    self.canvas.winfo_width() // 2,
                    self.canvas.winfo_height() // 2,
                    text="Camera Error\nNo image available",
                    fill=Colors.RED,
                    font=('Arial', 14),
                    justify=tk.CENTER
                )
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text=f"Camera Error\n{str(e)}",
                fill=Colors.RED,
                font=('Arial', 14),
                justify=tk.CENTER
            )
        
        if self.preview_active:
            self.after(33, self.update_preview)  # ~30 FPS

class TimeClockUI(ttk.Frame):
    def __init__(self, parent, settings_path: str = 'settings.json'):
        super().__init__(parent)
        self.settings = self._load_settings(settings_path)
        
        # Initialize services
        self.camera_service = CameraService(settings_path)
        self.soap_client = SoapClient(settings_path)
        
        self.employee_id = tk.StringVar()
        self.status_text = tk.StringVar()
        self.status_text_es = tk.StringVar()
        
        self.create_widgets()
        self.reset_ui()
        
        # Bind keyboard input
        parent.bind('<Key>', self.on_key_press)
        parent.bind('<Return>', self.process_punch)
        parent.bind(self.settings['ui']['adminShortcut'], self.show_admin_panel)

    def show_admin_panel(self, event=None):
        """Show the admin panel"""
        from admin_panel import AdminLoginDialog, AdminPanel
        
        def on_login(success: bool):
            if success:
                AdminPanel(self.winfo_toplevel())
        
        AdminLoginDialog(self.winfo_toplevel(), on_login)

    def _load_settings(self, settings_path: str) -> dict:
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise

    def create_widgets(self):
        # Configure style
        style = ttk.Style()
        style.configure('Clock.TFrame', background=Colors.WHITE)
        
        # Main container with padding
        main_container = ttk.Frame(self, padding="20", style='Clock.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Top section with time
        self.timer_label = TimerLabel(main_container)
        self.timer_label.pack(pady=(0, 20))
        
        # Middle section with status and camera
        middle_frame = ttk.Frame(main_container)
        middle_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status labels (English and Spanish)
        status_frame = ttk.Frame(middle_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_text,
            font=('Arial', 24),
            foreground=Colors.BLACK
        )
        self.status_label.pack()
        
        self.status_label_es = ttk.Label(
            status_frame,
            textvariable=self.status_text_es,
            font=('Arial', 24),
            foreground=Colors.BLACK
        )
        self.status_label_es.pack()
        
        # Camera preview
        self.camera_preview = CameraPreview(middle_frame, self.camera_service)
        self.camera_preview.pack(pady=10)
        
        # Bottom section with ID entry
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Hidden entry for ID
        self.id_entry = ttk.Entry(
            bottom_frame,
            textvariable=self.employee_id,
            font=('Arial', 14)
        )
        self.id_entry.pack()
        self.id_entry.bind('<Return>', self.process_punch)

    def reset_ui(self):
        """Reset UI to initial state"""
        self.employee_id.set("")
        self.set_status("Please scan your ID", "Por favor pase su tarjeta", Colors.BLACK)
        self.camera_preview.stop_preview()

    def set_status(self, text: str, text_es: str, color: str):
        """Update status display"""
        self.status_text.set(text)
        self.status_text_es.set(text_es)
        self.status_label.configure(foreground=color)
        self.status_label_es.configure(foreground=color)

    def on_key_press(self, event):
        """Handle keyboard input"""
        if event.char.isprintable():
            self.id_entry.focus()

    def process_punch(self, event=None):
        """Process an employee punch"""
        employee_id = self.employee_id.get().strip()
        if not employee_id:
            return
        
        try:
            # Start camera preview
            self.camera_service.initialize()
            self.camera_preview.start_preview()
            
            # Capture photo
            photo_data = self.camera_service.capture_photo(employee_id)
            
            # Record punch
            response = self.soap_client.record_punch(
                employee_id=employee_id,
                punch_time=datetime.now(),
                image_data=photo_data
            )
            
            # Handle response
            if response['offline']:
                self.set_status(
                    "Punch saved offline",
                    "Datos guardados sin conexión",
                    Colors.GREY
                )
            elif response['success']:
                if response['punchType'].lower() == 'checkin':
                    self.set_status(
                        f"Welcome {response['firstName']}!",
                        f"¡Bienvenido {response['firstName']}!",
                        Colors.GREEN
                    )
                else:
                    self.set_status(
                        f"Goodbye {response['firstName']}!",
                        f"¡Adiós {response['firstName']}!",
                        Colors.GREEN
                    )
            else:
                self.set_status(
                    "Punch failed - Please try again",
                    "Error - Por favor intente de nuevo",
                    Colors.RED
                )
            
        except Exception as e:
            logger.error(f"Error processing punch: {e}")
            self.set_status(
                "System Error - Please try again",
                "Error del sistema - Por favor intente de nuevo",
                Colors.RED
            )
        
        finally:
            # Clean up
            self.employee_id.set("")
            self.camera_preview.stop_preview()
            self.camera_service.cleanup()
            
            # Reset UI after delay
            self.after(3000, self.reset_ui)

if __name__ == "__main__":
    # Test UI
    root = tk.Tk()
    root.title("Time Clock")
    
    # Configure root window
    root.configure(background=Colors.WHITE)
    
    app = TimeClockUI(root)
    app.pack(fill=tk.BOTH, expand=True)
    
    # Configure for fullscreen
    root.attributes('-fullscreen', True)
    root.mainloop()