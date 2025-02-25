import os
import sys
import logging
import customtkinter
from tkinter import messagebox
from datetime import datetime
import json
from time_clock_ui import TimeClockUI
from admin_panel import show_admin_login, AdminPanel
from soap_client import SoapClient
from camera_service import CameraService
from ui_theme import setup_theme

# Import Windows-specific modules if on Windows
if sys.platform == 'win32':
    try:
        import win32gui
        import win32con
        import win32api
    except ImportError:
        logging.warning("win32 modules not available. Some focus management features will be disabled.")

# Configure logging
def setup_logging():
    log_dir = "logs"
    try:
        # Try to create logs directory with full permissions
        os.makedirs(log_dir, exist_ok=True)
        if sys.platform == 'win32':
            import win32security
            import ntsecuritycon as con
            
            # Get the SID for the Users group
            users = win32security.ConvertStringSidToSid("S-1-5-32-545")
            
            # Set full control permissions for Users group
            security = win32security.SECURITY_DESCRIPTOR()
            security.SetSecurityDescriptorDacl(1, None, 0)
            
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                con.FILE_ALL_ACCESS,
                users
            )
            
            security.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(
                log_dir,
                win32security.DACL_SECURITY_INFORMATION,
                security
            )
        
        # Configure logging with simplified format (timestamp and message only)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'app.log')),
                logging.StreamHandler(sys.stdout)
            ]
        )
    except Exception as e:
        # If we can't write to logs, fall back to console only
        print(f"Warning: Could not set up file logging: {e}")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

class TimeClock:
    def __init__(self):
        self.settings = self.load_settings()
        
        # Configure Windows-specific focus settings
        if sys.platform == 'win32':
            self.configure_windows_focus()
            
        self.setup_root_window()
        self.init_services()
        self.create_ui()
        
        # Add application start separator
        logging.info("="*50)
        logging.info(f"APPLICATION START - {datetime.now().strftime('%A, %B %d, %Y %I:%M:%S %p')}")
        logging.info("="*50)
        
        # Schedule periodic tasks
        self.schedule_tasks()
        
    def configure_windows_focus(self):
        """Configure Windows-specific focus settings"""
        try:
            import win32gui
            import win32con
            import ctypes
            from ctypes import wintypes
            
            logging.info("Configuring Windows-specific focus settings")
            
            # Try to set the app as DPI aware to prevent scaling issues
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            except Exception as e:
                logging.warning(f"Failed to set DPI awareness: {e}")
            
            # Try to disable Windows notifications during app runtime
            try:
                # Define necessary constants and structures
                class FLASHWINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", wintypes.UINT),
                        ("hwnd", wintypes.HWND),
                        ("dwFlags", wintypes.DWORD),
                        ("uCount", wintypes.UINT),
                        ("dwTimeout", wintypes.DWORD)
                    ]
                
                # Set app to be more resistant to focus stealing
                SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2000
                SPIF_SENDCHANGE = 0x2
                ctypes.windll.user32.SystemParametersInfoW(
                    SPI_SETFOREGROUNDLOCKTIMEOUT,
                    0,
                    0,  # Setting to 0 makes focus switching more immediate
                    SPIF_SENDCHANGE
                )
                
                # Try to disable Windows notifications during app runtime
                try:
                    # Windows 10/11 Focus Assist (Quiet Hours) API
                    # QUERY_USER_NOTIFICATION_STATE enum values:
                    # 1 = QUNS_BUSY - Do not disturb, no notifications
                    # 2 = QUNS_RUNNING_D3D_FULL_SCREEN - Full-screen app running
                    # 3 = QUNS_PRESENTATION_MODE - Presentation mode
                    # 4 = QUNS_ACCEPTS_NOTIFICATIONS - Normal, show notifications
                    # 5 = QUNS_QUIET_HOURS - Quiet hours, no notifications
                    
                    # Load the DLL
                    shell32 = ctypes.WinDLL("shell32.dll")
                    
                    # Note: We've removed the SetSuspendState call that was causing hibernation issues
                    logging.info("Windows notification settings configured")
                        
                except Exception as e:
                    logging.warning(f"Failed to configure Windows notification settings: {e}")
                
                logging.info("Windows focus settings configured successfully")
            except Exception as e:
                logging.warning(f"Failed to configure Windows focus settings: {e}")
                
        except ImportError as e:
            logging.warning(f"Windows modules not available for focus configuration: {e}")
    
    # Removed detect_and_configure_kiosk_mode function

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
                "fullscreen": True,
                "language": "en",
                "adminShortcut": "ctrl+alt+a",
                "adminPassword": "Metro2024!"
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
            # Try to load existing settings
            try:
                with open('settings.json', 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
                # Create default settings if file doesn't exist
                logging.info("Settings file not found, creating default settings")
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
        
        # Set window icon if available
        if os.path.exists('app.ico'):
            self.root.iconbitmap('app.ico')
        
        # Configure basic window properties
        self.root.minsize(window_width, window_height)
        self.root.maxsize(window_width, window_height)
        self.root.resizable(False, False)
        
        if self.settings['ui'].get('fullscreen', True):
            # Remove window decorations first
            self.root.overrideredirect(True)
            
            # Set window properties
            self.root.attributes('-topmost', True)
            
            # Calculate position to center the window
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            
            # Position window at center
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # Update to ensure geometry is applied
            self.root.update_idletasks()
            
            # Ensure window is properly focused
            self.root.focus_force()
            
            # Log focus state
            logging.info("Initial focus state: focused")
        else:
            # For non-fullscreen mode, center the window
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
        # Ensure window is ready and visible
        self.root.update_idletasks()
        self.root.lift()
            
        # Prevent alt+f4
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind admin shortcut to root window
        self.root.bind(self.settings['ui']['adminShortcut'], self.show_admin_dialog)
        
        # Focus monitoring removed

    def init_services(self):
        try:
            # Initialize services
            self.soap_client = SoapClient()
            self.camera_service = CameraService()
            
            # Test camera initialization
            if not self.camera_service.initialize():
                logging.error("Failed to initialize camera")
                messagebox.showwarning(
                    "Warning",
                    "Failed to initialize camera. Photo capture will be disabled."
                )
            
        except Exception as e:
            logging.error(f"Failed to initialize services: {e}")
            messagebox.showerror(
                "Error",
                "Failed to initialize required services. The application may not function correctly."
            )

    def create_ui(self):
        # Create main UI with settings
        self.time_clock_ui = TimeClockUI(self.root, settings=self.settings)
        self.time_clock_ui.pack(fill="both", expand=True)

    def schedule_tasks(self):
        # Schedule periodic tasks
        
        # Sync offline punches every 5 minutes
        self.root.after(300000, self.sync_offline_data)
        
        # Clean old records daily
        self.root.after(86400000, self.cleanup_old_records)
        
        # Check camera connection every hour
        self.root.after(3600000, self.check_camera)
        
        # Check for day change every minute
        self.last_day = datetime.now().day
        self.root.after(60000, self.check_day_change)

    def check_day_change(self):
        """Check if day has changed and add separator to logs"""
        current_day = datetime.now().day
        if current_day != self.last_day:
            # Add separator for new day
            logging.info("="*50)
            logging.info(f"MSI Time Clock - {datetime.now().strftime('%A, %B %d, %Y')}")
            logging.info("="*50)
            self.last_day = current_day
        
        # Reschedule check
        self.root.after(60000, self.check_day_change)

    def sync_offline_data(self):
        """Sync offline punch data"""
        try:
            results = self.soap_client.sync_offline_punches()
            logging.info(f"Offline sync results: {results}")
        except Exception as e:
            logging.error(f"Failed to sync offline data: {e}")
        finally:
            # Reschedule
            self.root.after(300000, self.sync_offline_data)

    def cleanup_old_records(self):
        """Clean up old records"""
        try:
            count = self.soap_client.cleanup_old_records()
            logging.info(f"Cleaned up {count} old records")
        except Exception as e:
            logging.error(f"Failed to cleanup old records: {e}")
        finally:
            # Reschedule
            self.root.after(86400000, self.cleanup_old_records)

    def check_camera(self):
        """Check camera connection"""
        try:
            if not self.camera_service.initialize():
                logging.warning("Camera check failed - attempting to reinitialize")
                # Attempt to reinitialize
                self.camera_service.cleanup()
                if not self.camera_service.initialize():
                    logging.error("Failed to reinitialize camera")
        except Exception as e:
            logging.error(f"Camera check failed: {e}")
        finally:
            # Cleanup
            self.camera_service.cleanup()
            # Reschedule
            self.root.after(3600000, self.check_camera)

    def show_admin_dialog(self, event=None):
        """Show admin login dialog"""
        def on_login(success: bool):
            if success:
                # Create admin panel as a Toplevel window
                admin_panel = AdminPanel(self.root)
                
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
                admin_panel.grab_set()  # Make 008000it modal
                admin_panel.focus_force()  # Ensure focus
        
        show_admin_login(self.root, on_login)

    # Focus event handlers removed
    
    # Focus checking method removed
    
    # Dialog detection method removed
    
    # Focus recapture method removed

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
