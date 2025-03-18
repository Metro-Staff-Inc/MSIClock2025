"""
Windows implementation of the MSI Time Clock application.
This module provides the Windows-specific entry point and initialization.
This version does not support camera functionality.
"""

import os
import sys
import logging
from datetime import datetime
import customtkinter
from tkinter import messagebox

from msi_core.soap.client import SoapClient
from platforms.windows.config import WindowsSettingsManager
from platforms.windows.ui.time_clock_ui import TimeClockUI
from platforms.windows.ui.admin_panel import show_admin_login, AdminPanel
from platforms.windows.ui.ui_theme import setup_theme

logger = logging.getLogger(__name__)

class WindowsTimeClock:
    """Windows implementation of the MSI Time Clock"""
    
    def __init__(self):
        """Initialize the Windows time clock application"""
        # Initialize settings with Windows-specific manager
        self.settings_manager = WindowsSettingsManager()
        self.settings = self.settings_manager.get_settings()
        
        # Set up UI
        self.setup_root_window()
        
        # Initialize services
        self.init_services()
        
        # Create UI
        self.create_ui()
        
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
        window_width = 1024
        window_height = 768
        
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
            soap_client=self.soap_client
        )
        self.time_clock_ui.pack(fill="both", expand=True)

    def schedule_tasks(self):
        """Schedule periodic maintenance tasks"""
        # Try to reconnect if offline every minute
        self.root.after(60000, self.check_connection)
        
        # Sync offline punches every 5 minutes
        self.root.after(300000, self.sync_offline_data)
        
        # Clean old records daily
        self.root.after(86400000, self.cleanup_old_records)

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

    def show_admin_panel(self, event=None):
        """Show the admin panel"""
        def on_login(success: bool):
            if success:
                self.show_admin_panel_direct()
        
        show_admin_login(self.root, on_login)

    def show_admin_panel_direct(self):
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

def main():
    """Windows platform entry point"""
    try:
        app = WindowsTimeClock()
        app.run()
    except Exception as e:
        logger.error(f"Failed to start Windows application: {e}")
        messagebox.showerror(
            "Error",
            "Failed to start application. Please check the logs for details."
        )
        sys.exit(1)

if __name__ == "__main__":
    main()