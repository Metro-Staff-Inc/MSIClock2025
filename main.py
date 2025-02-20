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
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

class TimeClock:
    def __init__(self):
        self.settings = self.load_settings()
        self.setup_root_window()
        self.init_services()
        self.create_ui()
        
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
                    "width": 320,
                    "height": 240
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
        
        # Force 800x600 for testing
        self.root.geometry("800x600")
        self.root.resizable(False, False)  # Prevent resizing
        
        '''
        # Set fullscreen
        if self.settings['ui']['fullscreen']:
            self.root.attributes('-fullscreen', True)
        '''
            
        # Prevent alt+f4
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind admin shortcut
        self.root.bind(self.settings['ui']['adminShortcut'], self.show_admin_dialog)

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
        # Create main UI
        self.time_clock_ui = TimeClockUI(self.root)
        self.time_clock_ui.pack(fill="both", expand=True)

    def schedule_tasks(self):
        # Schedule periodic tasks
        
        # Sync offline punches every 5 minutes
        self.root.after(300000, self.sync_offline_data)
        
        # Clean old records daily
        self.root.after(86400000, self.cleanup_old_records)
        
        # Check camera connection every hour
        self.root.after(3600000, self.check_camera)

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
                AdminPanel(self.root)
        
        show_admin_login(self.root, on_login)

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
    
    # Log startup
    logging.info("Starting MSI Time Clock application")
    
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
