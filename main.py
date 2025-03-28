import os
import sys
import logging
import customtkinter
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import json
from time_clock_ui import TimeClockUI
from admin_panel import show_admin_login, AdminPanel
from soap_client import SoapClient
from camera_service import CameraService
from ui_theme import setup_theme
from password_utils import hash_password

# Custom auto-closing message box
class AutoClosingMessageBox:
    def __init__(self, title, message, timeout=5, message_type="info"):
        """
        Create an auto-closing message box
        
        Args:
            title: Title of the message box
            message: Message to display
            timeout: Time in seconds before auto-closing (default: 5)
            message_type: Type of message box ("info", "warning", or "error")
        """
        self.timeout = timeout
        self.root = tk.Toplevel()
        self.root.title(title)
        self.root.resizable(False, False)
        
        # Set icon based on message type
        if message_type == "warning":
            self.root.iconwarning()
        elif message_type == "error":
            self.root.iconerror()
        else:
            self.root.iconinfo()
            
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        
        # Message label
        self.label = tk.Label(self.root, text=message, padx=20, pady=20, wraplength=300)
        self.label.grid(row=0, column=0, sticky="nsew")
        
        # OK button with countdown
        self.button_text = tk.StringVar()
        self.button_text.set(f"OK ({self.timeout})")
        self.button = tk.Button(self.root, textvariable=self.button_text, command=self.close)
        self.button.grid(row=1, column=0, pady=(0, 10))
        
        # Center the window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Start countdown
        self.countdown()
        
        # Make modal
        self.root.transient()
        self.root.grab_set()
        
    def countdown(self):
        """Update countdown and close when reaching zero"""
        if self.timeout > 0:
            self.button_text.set(f"OK ({self.timeout})")
            self.timeout -= 1
            self.root.after(1000, self.countdown)
        else:
            self.close()
            
    def close(self):
        """Close the message box"""
        self.root.grab_release()
        self.root.destroy()

# Wrapper functions for standard message boxes
def show_auto_info(title, message, timeout=5):
    """Show auto-closing info message box"""
    return AutoClosingMessageBox(title, message, timeout, "info")
    
def show_auto_warning(title, message, timeout=5):
    """Show auto-closing warning message box"""
    return AutoClosingMessageBox(title, message, timeout, "warning")
    
def show_auto_error(title, message, timeout=5):
    """Show auto-closing error message box"""
    return AutoClosingMessageBox(title, message, timeout, "error")

# Configure logging
def setup_logging():
    log_dir = "logs"
    try:
        # Create logs directory with proper permissions
        os.makedirs(log_dir, mode=0o777, exist_ok=True)
        
        # Try to load settings to get log level
        log_level = logging.INFO  # Default to INFO
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                level_str = settings.get('logging', {}).get('level', 'INFO')
                log_level = getattr(logging, level_str)
                print(f"Setting log level to: {level_str}")
        except Exception as e:
            print(f"Could not load log level from settings: {e}")
        
        # Create custom formatter that handles both normal and separator formats
        class CustomFormatter(logging.Formatter):
            def format(self, record):
                # Special handling for separator messages
                if record.msg.startswith('='*50) or record.msg.startswith('APPLICATION START'):
                    return record.getMessage()
                
                # Normal message handling
                original_levelname = record.levelname
                # Only show level if not INFO
                if record.levelno == logging.INFO:
                    record.levelname = ""
                # Format with timestamp
                result = f"{self.formatTime(record)} - {record.levelname} - {record.getMessage()}"
                # Restore original levelname
                record.levelname = original_levelname
                # Clean up extra dash for INFO level
                if record.levelno == logging.INFO:
                    result = result.replace(" -  -", " -")
                return result

        # Configure logging with custom formatter
        formatter = CustomFormatter('%(asctime)s - %(levelname)s - %(message)s')
        handlers = [
            logging.FileHandler(os.path.join(log_dir, 'app.log')),
            logging.StreamHandler(sys.stdout)
        ]
        for handler in handlers:
            handler.setFormatter(formatter)
        
        logging.basicConfig(
            level=log_level,
            handlers=handlers
        )
        
        # Set all loggers to the configured level
        for logger_name in logging.root.manager.loggerDict:
            logging.getLogger(logger_name).setLevel(log_level)
            
        # Log the level that was set
        logging.debug(f"Logging initialized with level: {logging.getLevelName(log_level)}")
        
    except Exception as e:
        # If we can't write to logs, fall back to console only
        print(f"Warning: Could not set up file logging: {e}")
        # Use same custom formatter for fallback logging
        fallback_handler = logging.StreamHandler(sys.stdout)
        fallback_handler.setFormatter(CustomFormatter())
        logging.basicConfig(
            level=logging.DEBUG,  # Use DEBUG for fallback to capture everything
            handlers=[fallback_handler]
        )

class TimeClock:
    def __init__(self):
        self.settings = self.load_settings()
            
        self.setup_root_window()
        self.init_services()
        self.create_ui()
        
        # Add application start separator
        logging.info("="*50)
        logging.info(f"APPLICATION START - {datetime.now().strftime('%A, %B %d, %Y %I:%M:%S %p')}")
        logging.info("="*50)
        
        # Check if this is first launch and show admin panel
        if self.settings.get('ui', {}).get('firstLaunch', True):
            logging.info("First launch detected, showing welcome dialog")
            
            # Create themed welcome dialog
            welcome_dialog = customtkinter.CTkToplevel(self.root)
            welcome_dialog.title("FIRST LAUNCH")
            welcome_dialog.attributes('-topmost', True)
            
            # Set size and position
            dialog_width = 400
            dialog_height = 200
            x = (welcome_dialog.winfo_screenwidth() - dialog_width) // 2
            y = (welcome_dialog.winfo_screenheight() - dialog_height) // 2
            welcome_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            
            # Add welcome message
            customtkinter.CTkLabel(
                welcome_dialog,
                text="This is the first launch of the MSI Time Clock on this computer.\n\nPlease configure your settings in the admin panel.",
                font=('IBM Plex Sans Medium', 14),
                wraplength=350
            ).pack(pady=20)
            
            # Add OK button
            def on_welcome_close():
                welcome_dialog.destroy()
                # Show admin panel directly without password prompt
                self.show_admin_panel_direct(first_launch=True)
            
            customtkinter.CTkButton(
                welcome_dialog,
                text="OK",
                command=on_welcome_close,
                width=100,
                height=35,
                fg_color="#A4D233",
                hover_color="#8AB22B",
                text_color="#000000"
            ).pack(pady=20)
            
            welcome_dialog.transient(self.root)
            welcome_dialog.grab_set()
        
        # Schedule periodic tasks
        self.schedule_tasks()
        
    def create_default_settings(self):
        default_settings = {
            "soap": {
                "username": "",
                "password": "",
                "endpoint": "http://msiwebtrax.com/",
                "timeout": 30,
                "clientId": 185
            },
            "camera": {
                "deviceId": 0,
                "captureQuality": 85,
                "resolution": {
                    "width": 640,
                    "height": 480
                }
            },
            "ui": {
                "fullscreen": False,
                "language": "en",
                "adminShortcut": "ctrl+alt+a",
                "adminPassword": hash_password("Metro2024!"),
                "firstLaunch": True
            },
            "storage": {
                "retentionDays": 30,
                "dbPath": "data/local.db",
                "maxOfflineRecords": 10000
            },
            "logging": {
                "level": "INFO",
                "maxSize": 10485760,
                "backupCount": 5
            }
        }
        
        try:
            with open('settings.json', 'w') as f:
                json.dump(default_settings, f, indent=2)
            return default_settings
        except Exception as e:
            logging.error(f"Failed to create default settings: {e}")
            raise

    def load_settings(self):
        try:
            # Get default settings structure
            default_settings = {
                "soap": {
                    "username": "",
                    "password": "",
                    "endpoint": "http://msiwebtrax.com/",
                    "timeout": 30,
                    "clientId": 185
                },
                "camera": {
                    "deviceId": 0,
                    "captureQuality": 85,
                    "resolution": {
                        "width": 640,
                        "height": 480
                    }
                },
                "ui": {
                    "fullscreen": True,
                    "language": "en",
                    "adminShortcut": "ctrl+alt+a",
                    "adminPassword": "Metro2024!",
                    "firstLaunch": True
                },
                "storage": {
                    "retentionDays": 30,
                    "dbPath": "data/local.db",
                    "maxOfflineRecords": 10000
                },
                "logging": {
                    "level": "INFO",
                    "maxSize": 10485760,
                    "backupCount": 5
                }
            }
            
            try:
                # Try to load existing settings
                with open('settings.json', 'r') as f:
                    current_settings = json.load(f)
                
                logging.debug("Loaded current settings: %s", current_settings)
                    
                # Deep merge function to preserve existing values while adding missing ones
                def deep_merge(source, destination):
                    # Deep merge without modifying firstLaunch
                    for key, value in source.items():
                        if key in destination:
                            if isinstance(value, dict) and isinstance(destination[key], dict):
                                deep_merge(value, destination[key])
                        else:
                            destination[key] = value
                    return destination
                
                # Merge settings, keeping existing values but adding any missing fields
                merged_settings = deep_merge(default_settings, current_settings)
                
                # Ensure the settings are saved with any missing fields added
                with open('settings.json', 'w') as f:
                    json.dump(merged_settings, f, indent=2)
                
                return merged_settings
                
            except FileNotFoundError:
                # Create default settings if file doesn't exist
                logging.debug("Settings file not found, creating default settings")
                return self.create_default_settings()
            except Exception as e:
                logging.error(f"Failed to load settings: {e}")
                messagebox.showerror(
                    "Error",
                    "Failed to load settings. Please check settings.json file."
                )
                sys.exit(1)
        except Exception as e:
            logging.error(f"Failed to handle settings: {e}")
            messagebox.showerror(
                "Error",
                "Failed to create or load settings. Please check permissions."
            )
            sys.exit(1)

    def setup_root_window(self):
        # Setup theme before creating window
        setup_theme()
        
        self.root = customtkinter.CTk()
        self.root.title("MSI Time Clock")
        customtkinter.set_appearance_mode("dark")
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Set fixed window size
        window_width = 800
        window_height = 600
        
        # Update the settings
        if 'ui' not in self.settings:
            self.settings['ui'] = {}
        self.settings['ui']['scaling_factor'] = 1.0  # No scaling
        
        # Set window icon using .png format
        try:
            icon_path = os.path.join('assets', 'people-dark-bg.png')
            if os.path.exists(icon_path):
                from PIL import Image, ImageTk
                icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                self.root.iconphoto(True, icon_img)
        except Exception as e:
            logging.warning(f"Could not set application icon: {e}")
        
        # Set window size and position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Set window properties
        self.root.minsize(window_width, window_height)
        self.root.resizable(True, True)
        
        # Create toolbar frame
        self.toolbar = customtkinter.CTkFrame(self.root, height=30)
        self.toolbar.pack(fill="x", side="top")
        
        # Add fullscreen toggle button
        self.fullscreen_btn = customtkinter.CTkButton(
            self.toolbar,
            text="⛶",  # Unicode symbol for fullscreen
            width=30,
            height=25,
            command=self.toggle_fullscreen
        )
        self.fullscreen_btn.pack(side="right", padx=5, pady=2)
        
        # Initialize fullscreen state from settings
        self._fullscreen = self.settings.get('ui', {}).get('fullscreen', False)
        if self._fullscreen:
            self.root.attributes('-fullscreen', True)
            self.toolbar.pack_forget()
            self.fullscreen_btn.configure(text="❐")
        
        # Create main content frame
        self.content_frame = customtkinter.CTkFrame(self.root)
        self.content_frame.pack(fill="both", expand=True)
        
        # Update to ensure geometry is applied
        self.root.update_idletasks()
        self.root.lift()
        
        # Prevent alt+f4
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind admin shortcut to root window
        self.root.bind('<Control-Alt-a>', self.show_admin_panel)  # Explicit binding
        self.root.bind(self.settings['ui']['adminShortcut'], self.show_admin_panel)  # Settings-based binding
        
        # Focus monitoring removed

    def init_services(self):
        try:
            # Initialize services
            self.soap_client = SoapClient()
            if not self.soap_client.is_online():
                error = self.soap_client.get_connection_error()
                logging.warning(f"Starting in offline mode: {error}")
                show_auto_warning(
                    "Network Warning",
                    "Starting in offline mode. Punches will be stored locally and synced when connection is restored."
                )

            self.camera_service = CameraService()
            
            # Test camera initialization
            if not self.camera_service.initialize():
                logging.error("Failed to initialize camera")
                show_auto_warning(
                    "Warning",
                    "Failed to initialize camera. Photo capture will be disabled."
                )
            
        except Exception as e:
            logging.error(f"Failed to initialize services: {e}")
            show_auto_error(
                "Error",
                "Failed to initialize required services. The application will start in offline mode."
            )

    def create_ui(self):
        # Create main UI with settings in the content frame
        # Pass the camera_service to TimeClockUI to avoid creating multiple instances
        self.content_frame.camera_service = self.camera_service
        self.time_clock_ui = TimeClockUI(self.content_frame, settings=self.settings)
        self.time_clock_ui.pack(fill="both", expand=True)

    def schedule_tasks(self):
        # Schedule periodic tasks
        
        # Try to reconnect if offline every minute
        self.root.after(60000, self.check_connection)
        
        # Sync offline punches every 5 minutes
        self.root.after(300000, self.sync_offline_data)
        
        # Clean old records daily
        self.root.after(86400000, self.cleanup_old_records)
        
        # Check camera connection every hour
        self.root.after(3600000, self.check_camera)
        
        # Check for day change every minute
        self.last_day = datetime.now().day
        self.root.after(60000, self.check_day_change)

    def _schedule_periodic_task(self, task, delay):
        """Schedule a periodic task with error handling"""
        def wrapped_task():
            try:
                task()
            except Exception as e:
                logging.error(f"Error in periodic task {task.__name__}: {e}")
            finally:
                try:
                    self.root.after(delay, wrapped_task)
                except Exception as e:
                    logging.error(f"Failed to reschedule {task.__name__}: {e}")
                    # Emergency reschedule attempt
                    try:
                        self.root.after(delay * 2, wrapped_task)  # Try again with double delay
                    except Exception as e:
                        logging.critical(f"Failed emergency reschedule of {task.__name__}: {e}")
        
        # Initial schedule
        try:
            self.root.after(delay, wrapped_task)
        except Exception as e:
            logging.error(f"Failed to schedule {task.__name__}: {e}")

    def check_connection(self):
        """Check connection status and attempt reconnection if offline"""
        if not self.soap_client.is_online():
            if self.soap_client.try_reconnect():
                logging.info("Successfully reconnected to SOAP service")
            else:
                error = self.soap_client.get_connection_error()
                logging.debug(f"Still offline: {error}")

    def check_day_change(self):
        """Check if day has changed and add separator to logs"""
        current_day = datetime.now().day
        if current_day != self.last_day:
            # Add separator for new day
            logging.info("="*50)
            logging.info(f"MSI Time Clock - {datetime.now().strftime('%A, %B %d, %Y')}")
            logging.info("="*50)
            self.last_day = current_day

    def sync_offline_data(self):
        """Sync offline punch data"""
        # Only attempt sync if we're online
        if self.soap_client.is_online():
            results = self.soap_client.sync_offline_punches()
            logging.debug(f"Offline sync results: {results}")
            
            # Show success message if any punches were synced
            if results.get('synced', 0) > 0:
                show_auto_info(
                    "Sync Complete",
                    f"Successfully synced {results['synced']} offline punches."
                )
            
            # Show warning if any failed
            if results.get('failed', 0) > 0:
                show_auto_warning(
                    "Sync Warning",
                    f"Failed to sync {results['failed']} offline punches. Will retry later."
                )
        else:
            logging.debug("Skipping offline sync - system is offline")

    def cleanup_old_records(self):
        """Clean up old records"""
        count = self.soap_client.cleanup_old_records()
        logging.debug(f"Cleaned up {count} old records")

    def check_camera(self):
        """Check camera connection"""
        logging.debug("Periodic camera check running")
        
        # Check if camera is initialized without reinitializing
        if hasattr(self.camera_service, 'is_initialized') and self.camera_service.is_initialized:
            logging.debug("Camera is already initialized, skipping check")
            return
            
        # Only try to initialize if it's not already initialized
        if not self.camera_service.initialize():
            logging.warning("Camera check failed - attempting to reinitialize")
            # Attempt to reinitialize
            self.camera_service.cleanup()
            if not self.camera_service.initialize():
                logging.error("Failed to reinitialize camera")

    def show_admin_panel_direct(self, first_launch=False):
        """Show admin panel directly without password prompt"""
        # Create admin panel as a Toplevel window with settings path
        admin_panel = AdminPanel(self.root, settings_path='settings.json')
        logging.debug("Created admin panel with settings path")
        
        # Get screen dimensions
        screen_width = admin_panel.winfo_screenwidth()
        screen_height = admin_panel.winfo_screenheight()
        
        # Set size based on screen dimensions
        panel_width = int(screen_width * 0.8)  # 80% of screen width
        panel_height = int(screen_height * 0.8)  # 80% of screen height
        
        # Center the window
        x = (screen_width - panel_width) // 2
        y = (screen_height - panel_height) // 2
        
        # Set geometry and properties
        admin_panel.geometry(f"{panel_width}x{panel_height}+{x}+{y}")
        admin_panel.minsize(800, 600)
        admin_panel.attributes('-topmost', True)  # Keep on top
        admin_panel.transient(self.root)  # Set as transient to main window
        admin_panel.grab_set()  # Make it modal
        admin_panel.focus_force()  # Ensure focus

        # If this is first launch, update the flag when admin panel is closed
        if first_launch:
            def on_admin_close():
                admin_panel.destroy()
            
            admin_panel.protocol("WM_DELETE_WINDOW", on_admin_close)

    def show_admin_panel(self, event=None, first_launch=False):
        """Show admin login dialog"""
        if first_launch:
            # Skip password prompt on first launch
            self.show_admin_panel_direct(first_launch=True)
        else:
            def on_login(success: bool):
                if success:
                    logging.debug("Admin login successful, showing admin panel")
                    self.show_admin_panel_direct(first_launch=False)
            
            show_admin_login(self.root, on_login)

    # Focus event handlers removed
    
    # Focus checking method removed
    
    # Dialog detection method removed
    
    # Focus recapture method removed

    def toggle_fullscreen(self):
        """Toggle fullscreen state and toolbar visibility"""
        self._fullscreen = not self._fullscreen
        
        if self._fullscreen:
            # Save current geometry before going fullscreen
            self._last_geometry = self.root.geometry()
            # Hide toolbar
            self.toolbar.pack_forget()
            # Set fullscreen
            self.root.attributes('-fullscreen', True)
            self.fullscreen_btn.configure(text="❐")  # Unicode symbol for exit fullscreen
        else:
            # Exit fullscreen
            self.root.attributes('-fullscreen', False)
            # Show toolbar
            self.toolbar.pack(fill="x", side="top")
            # Restore previous geometry
            if hasattr(self, '_last_geometry'):
                self.root.geometry(self._last_geometry)
            self.fullscreen_btn.configure(text="⛶")  # Unicode symbol for enter fullscreen
        
        # Update settings
        self.settings['ui']['fullscreen'] = self._fullscreen
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save fullscreen setting: {e}")

    def on_closing(self):
        """Handle window close attempt"""
        # Only allow close through admin panel
        pass

    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except Exception as e:
            logging.error(f"Application error: {e}")
            messagebox.showerror("Error", f"Application error: {e}")
        finally:
            # Cleanup
            self.camera_service.cleanup()

def main():
    # Setup logging
    setup_logging()
    
    try:
        # Create and run application
        app = TimeClock()
        app.run()
    except Exception as e:
        logging.error(f"Failed to start application: {e}")
        messagebox.showerror(
            "Error",
            "Failed to start application. Please check the logs for details."
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
