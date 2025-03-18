"""
Android implementation of the MSI Time Clock application.
This module provides the Android-specific entry point and initialization.
"""

import os
import sys
import logging
from datetime import datetime
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock

from msi_core.soap.client import SoapClient
from platforms.android.config import AndroidSettingsManager
from platforms.android.ui.time_clock_ui import TimeClockUI
from platforms.android.ui.ui_theme import setup_theme

logger = logging.getLogger(__name__)

class MainScreen(Screen):
    """Main screen containing the time clock UI"""
    pass

class MSITimeClockApp(MDApp):
    """Android implementation of the MSI Time Clock"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize settings
        self.settings_manager = AndroidSettingsManager()
        self.settings = self.settings_manager.get_settings()
        
        # Initialize services
        self.init_services()
        
        # Create screen manager
        self.screen_manager = ScreenManager()

    def build(self):
        """Build the Kivy application"""
        # Set up theme
        setup_theme()
        
        # Create main screen
        main_screen = MainScreen(name='main')
        
        # Create time clock UI
        self.time_clock_ui = TimeClockUI(
            settings_manager=self.settings_manager,
            soap_client=self.soap_client
        )
        main_screen.add_widget(self.time_clock_ui)
        
        # Add main screen to manager
        self.screen_manager.add_widget(main_screen)
        
        # Log application start
        logger.info("="*50)
        logger.info(f"APPLICATION START - {datetime.now().strftime('%A, %B %d, %Y %I:%M:%S %p')}")
        logger.info("="*50)
        
        # Schedule periodic tasks
        self.schedule_tasks()
        
        return self.screen_manager

    def init_services(self):
        """Initialize required services"""
        try:
            # Initialize SOAP client
            self.soap_client = SoapClient()
            if not self.soap_client.is_online():
                error = self.soap_client.get_connection_error()
                logger.warning(f"Starting in offline mode: {error}")
                self.show_warning(
                    "Network Warning",
                    "Starting in offline mode. Punches will be stored locally and synced when connection is restored."
                )
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            self.show_error(
                "Error",
                "Failed to initialize required services. The application will start in offline mode."
            )

    def schedule_tasks(self):
        """Schedule periodic maintenance tasks"""
        # Try to reconnect if offline every minute
        Clock.schedule_interval(self.check_connection, 60)
        
        # Sync offline punches every 5 minutes
        Clock.schedule_interval(self.sync_offline_data, 300)
        
        # Clean old records daily
        Clock.schedule_interval(self.cleanup_old_records, 86400)

    def check_connection(self, *args):
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

    def sync_offline_data(self, *args):
        """Sync offline punch data"""
        try:
            if self.soap_client.is_online():
                results = self.soap_client.sync_offline_punches()
                logger.debug(f"Offline sync results: {results}")
                
                # Show success message if any punches were synced
                if results.get('synced', 0) > 0:
                    self.show_info(
                        "Sync Complete",
                        f"Successfully synced {results['synced']} offline punches."
                    )
                
                # Show warning if any failed
                if results.get('failed', 0) > 0:
                    self.show_warning(
                        "Sync Warning",
                        f"Failed to sync {results['failed']} offline punches. Will retry later."
                    )
            else:
                logger.debug("Skipping offline sync - system is offline")
                
        except Exception as e:
            logger.error(f"Failed to sync offline data: {e}")
            if self.soap_client.is_online():  # Only show error if we were supposed to be online
                self.show_error(
                    "Sync Error",
                    "Failed to sync offline punches. Will retry later."
                )

    def cleanup_old_records(self, *args):
        """Clean up old records"""
        try:
            count = self.soap_client.cleanup_old_records()
            logger.debug(f"Cleaned up {count} old records")
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")

    def show_error(self, title: str, message: str):
        """Show error dialog"""
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        
        dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def show_warning(self, title: str, message: str):
        """Show warning dialog"""
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        
        dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def show_info(self, title: str, message: str):
        """Show info dialog"""
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        
        dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

def main():
    """Android platform entry point"""
    try:
        app = MSITimeClockApp()
        app.run()
    except Exception as e:
        logger.error(f"Failed to start Android application: {e}")
        # On Android, we can't show a message box, so just log the error
        sys.exit(1)

if __name__ == "__main__":
    main()