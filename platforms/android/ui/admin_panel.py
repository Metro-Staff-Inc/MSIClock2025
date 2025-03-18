"""
Android-specific admin panel implementation for MSI Time Clock.
Uses KivyMD for Material Design components.
"""

import logging
from functools import partial
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from msi_core.auth.password_utils import verify_password

logger = logging.getLogger(__name__)

# Load the KV file
Builder.load_file('platforms/android/ui/admin_panel.kv')

class Tab(MDBoxLayout, MDTabsBase):
    """Base class for tabs"""
    pass

class AdminLoginDialog(MDDialog):
    """Dialog for admin login"""
    
    def __init__(self, settings_manager, callback, **kwargs):
        """Initialize the admin login dialog
        
        Args:
            settings_manager: Settings manager instance
            callback: Function to call with login result
        """
        self.settings_manager = settings_manager
        self.callback = callback
        super().__init__(**kwargs)

    def verify_password(self, password: str):
        """Verify the entered password
        
        Args:
            password: Password to verify
        """
        try:
            settings = self.settings_manager.get_settings()
            if verify_password(password, settings['ui']['adminPassword']):
                self.dismiss()
                self.callback(True)
            else:
                # Show error in password field
                password_field = self.ids.password_field
                password_field.error = True
                password_field.helper_text = "Invalid password"
                self.callback(False)
        except Exception as e:
            logger.error(f"Failed to verify password: {e}")
            self.callback(False)

def show_admin_login(parent, settings_manager, callback):
    """Show the admin login dialog
    
    Args:
        parent: Parent widget
        settings_manager: Settings manager instance
        callback: Function to call with login result
    """
    try:
        dialog = AdminLoginDialog(
            settings_manager=settings_manager,
            callback=callback
        )
        dialog.open()
    except Exception as e:
        logger.error(f"Failed to show admin login dialog: {e}")
        callback(False)

class AdminPanel(MDScreen):
    """Android admin panel implementation"""
    
    def __init__(self, settings_manager, **kwargs):
        """Initialize the admin panel
        
        Args:
            settings_manager: Settings manager instance
        """
        super().__init__(**kwargs)
        self.settings_manager = settings_manager
        self.settings = settings_manager.get_settings()
        
        # Load current settings
        self.load_current_settings()

    def load_current_settings(self):
        """Load current settings into UI"""
        try:
            # SOAP settings
            self.ids.client_id.text = str(self.settings['soap']['clientId'])
            self.ids.username.text = self.settings['soap']['username']
            self.ids.password.text = self.settings['soap']['password']
            
            # Storage settings
            self.ids.retention_days.text = str(self.settings['storage']['retentionDays'])
            self.ids.max_records.text = str(self.settings['storage']['maxOfflineRecords'])
            
        except Exception as e:
            logger.error(f"Failed to load current settings: {e}")
            self.show_error("Failed to load settings")

    def save_settings(self):
        """Save settings"""
        try:
            # Validate numeric fields
            try:
                client_id = int(self.ids.client_id.text)
                retention_days = int(self.ids.retention_days.text)
                max_records = int(self.ids.max_records.text)
            except ValueError:
                self.show_error("Please ensure all numeric fields contain valid numbers")
                return
            
            # Update settings
            self.settings['soap']['clientId'] = client_id
            self.settings['soap']['username'] = self.ids.username.text
            self.settings['soap']['password'] = self.ids.password.text
            
            self.settings['storage']['retentionDays'] = retention_days
            self.settings['storage']['maxOfflineRecords'] = max_records
            
            # Save settings
            self.settings_manager.save_settings(self.settings)
            
            # Show success message
            self.show_message("Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self.show_error(f"Failed to save settings: {e}")

    def show_error(self, message: str):
        """Show error dialog
        
        Args:
            message: Error message to display
        """
        dialog = MDDialog(
            title="Error",
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def show_message(self, message: str):
        """Show message dialog
        
        Args:
            message: Message to display
        """
        dialog = MDDialog(
            title="Success",
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def go_back(self):
        """Return to the main screen"""
        self.manager.switch_to_main()

    def close_application(self):
        """Show confirmation dialog for closing the application"""
        dialog = MDDialog(
            title="Confirm Close",
            text="Are you sure you want to close the application?",
            buttons=[
                MDFlatButton(
                    text="No",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Yes",
                    md_bg_color=self.theme_cls.error_color,
                    on_release=lambda x: self.confirm_close()
                )
            ]
        )
        dialog.open()

    def confirm_close(self):
        """Close the application"""
        from kivy.app import App
        App.get_running_app().stop()