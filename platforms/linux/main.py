"""
Linux implementation of the MSI Time Clock application.
This module provides the Linux-specific entry point and initialization.
"""

import os
import sys
import logging
from datetime import datetime
import customtkinter
from tkinter import messagebox

from msi_core.config.settings_manager import SettingsManager
from msi_core.camera.camera_linux import LinuxCamera
from msi_core.soap.client import SoapClient
from platforms.linux.ui.time_clock_ui import TimeClockUI
from platforms.linux.ui.admin_panel import show_admin_login, AdminPanel
from platforms.linux.ui.ui_theme import setup_theme

logger = logging.getLogger(__name__)

class LinuxTimeClock:
    """Linux implementation of the MSI Time Clock"""
    
    def __init__(self):
        """Initialize the Linux time clock application"""
        # Initialize settings
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.get_settings()
        
        # Set up UI
        self.setup_root_window()
        
        # Initialize services
        self.init_services()
        
        # Create UI
        self.create_ui()
        
        # Check if this is first launch and show admin panel
        if self.settings.get('ui', {}).get('firstLaunch', True):
            self.show_first_launch_dialog()
        
        # Schedule periodic tasks
        self.schedule_tasks()

    def setup_root_window(self):
        """Set up the main application window"""
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
        
        # Set window icon using .png format
        try:
            icon_path = os.path.join('assets', 'common', 'logo.png')
            if os.path.exists(icon_path):
                from PIL import Image, ImageTk
                icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                self.root.iconphoto(True, icon_img)
        except Exception as e:
            logger.warning(f"Could not set application icon: {e}")
        
        # Set window size and position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Set window properties
        self.root.minsize(window_width, window_height)
        self.root.resizable(True, True)
        
        # Prevent alt+f4
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind admin shortcut
        self.root.bind('<Control-Alt-a>', self.show_admin_panel)
        self.root.bind(self.settings['ui']['adminShortcut'], self.show_admin_panel)

    def init_services(self):
        """Initialize required services"""
        try:
            # Initialize services
            self.soap_client = SoapClient()
            if not self.soap_client.is_online():
                error = self.soap_client.get_connection_error()
                logger.warning(f"Starting in offline mode: {error}")
                messagebox.showwarning(
                    "Network Warning",
                    "Starting in offline mode. Punches will be stored locally and synced when connection is restored."
                )

            self.camera_service = LinuxCamera(self.settings_manager)
            
            # Test camera initialization
            if not self.camera_service.initialize():
                logger.error("Failed to initialize camera")
                messagebox.showwarning(
                    "Warning",
                    "Failed to initialize camera. Photo capture will be disabled."
                )
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            messagebox.showerror(
                "Error",
                "Failed to initialize required services. The application will start in offline mode."
            )

    def create_ui(self):
        """Create the main UI components"""
        # Create main UI with settings
        self.time_clock_ui = TimeClockUI(
            self.root,
            settings_manager=self.settings_manager,
            camera_service=self.camera_service,
            soap_client=self.soap_client
        )
        self.time_clock_ui.pack(fill="both", expand=True)

    def show_first_launch_dialog(self):
        """Show the first launch welcome dialog"""
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

    def schedule_tasks(self):
        """Schedule periodic maintenance tasks"""
        # Try to reconnect if offline every minute
        self.root.after(60000, self.check_connection)
        
        # Sync offline punches every 5 minutes
        self.root.after(300000, self.sync_offline_data)
        
        # Clean old records daily
        self.root.after(86400000, self.cleanup_old_records)
        
        # Check camera connection every hour
        self.root.after(3600000, self.check_camera)

    def check_connection(self):
        """Check connection status and attempt reconnection if offline"""
        try:
            if not self.soap_client.is_online():
                if self.soap_client.try_reconnect():
                    logger.info("Successfully reconnected to SOAP service")
                else:
                    error = self.soap_client.get_connection_error()
                    logger.debug(f"Still offline: {error}")
        except Exception as e:
            logger.error(f"Error checking connection: {e}")
        finally:
            # Reschedule check
            self.root.after(60000, self.check_connection)

    def sync_offline_data(self):
        """Sync offline punch data"""
        try:
            if self.soap_client.is_online():
                results = self.soap_client.sync_offline_punches()
                logger.debug(f"Offline sync results: {results}")
                
                # Show success message if any punches were synced
                if results.get('synced', 0) > 0:
                    messagebox.showinfo(
                        "Sync Complete",
                        f"Successfully synced {results['synced']} offline punches."
                    )
                
                # Show warning if any failed
                if results.get('failed', 0) > 0:
                    messagebox.showwarning(
                        "Sync Warning",
                        f"Failed to sync {results['failed']} offline punches. Will retry later."
                    )
            else:
                logger.debug("Skipping offline sync - system is offline")
                
        except Exception as e:
            logger.error(f"Failed to sync offline data: {e}")
            if self.soap_client.is_online():  # Only show error if we were supposed to be online
                messagebox.showerror(
                    "Sync Error",
                    "Failed to sync offline punches. Will retry later."
                )
        finally:
            # Reschedule
            self.root.after(300000, self.sync_offline_data)

    def cleanup_old_records(self):
        """Clean up old records"""
        try:
            count = self.soap_client.cleanup_old_records()
            logger.debug(f"Cleaned up {count} old records")
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
        finally:
            # Reschedule
            self.root.after(86400000, self.cleanup_old_records)

    def check_camera(self):
        """Check camera connection"""
        try:
            if not self.camera_service.is_initialized:
                logger.warning("Camera check failed - attempting to reinitialize")
                # Attempt to reinitialize
                self.camera_service.cleanup()
                if not self.camera_service.initialize():
                    logger.error("Failed to reinitialize camera")
        except Exception as e:
            logger.error(f"Camera check failed: {e}")
        finally:
            # Reschedule
            self.root.after(3600000, self.check_camera)

    def show_admin_panel(self, event=None):
        """Show the admin panel"""
        def on_login(success: bool):
            if success:
                self.show_admin_panel_direct()
        
        show_admin_login(self.root, on_login)

    def show_admin_panel_direct(self, first_launch: bool = False):
        """Show admin panel directly without password prompt"""
        admin_panel = AdminPanel(self.root, self.settings_manager)
        
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

    def on_closing(self):
        """Handle window close attempt"""
        # Only allow close through admin panel
        pass

    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Application error: {e}")
            messagebox.showerror("Error", f"Application error: {e}")
        finally:
            # Cleanup
            self.camera_service.cleanup()

def main():
    """Linux platform entry point"""
    try:
        app = LinuxTimeClock()
        app.run()
    except Exception as e:
        logger.error(f"Failed to start Linux application: {e}")
        messagebox.showerror(
            "Error",
            "Failed to start application. Please check the logs for details."
        )
        sys.exit(1)

if __name__ == "__main__":
    main()