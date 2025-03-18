"""
Windows-specific admin panel implementation for MSI Time Clock.
"""

import customtkinter
import logging
from typing import Callable
from msi_core.auth.password_utils import verify_password

logger = logging.getLogger(__name__)

def show_admin_login(parent, callback: Callable[[bool], None]):
    """Show admin login dialog and call callback with result
    
    Args:
        parent: Parent window
        callback: Function to call with login result
    """
    try:
        # Get settings from parent's settings manager
        settings = parent.settings_manager.get_settings()
        
        # Create dialog window
        dialog = customtkinter.CTkToplevel(parent)
        dialog.title("Admin Login")
        
        # Scale dialog size
        width = 300
        height = 180
        
        # Center on screen
        x = (dialog.winfo_screenwidth() - width) // 2
        y = (dialog.winfo_screenheight() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make it modal and ensure proper window management
        dialog.transient(parent)
        dialog.grab_set()
        dialog.focus_force()
        
        # Keep window on top
        dialog.lift()
        parent.lift(dialog)
        
        # Create password entry
        password_var = customtkinter.StringVar()
        
        scaled_fonts = {
            'title': ('Roboto', 14, 'bold'),
            'text': ('Roboto', 12),
            'button': ('Roboto', 12, 'bold')
        }
        
        # Create and pack widgets
        customtkinter.CTkLabel(
            dialog,
            text="Enter Admin Password:",
            font=scaled_fonts['text']
        ).pack(pady=(20, 10))
        
        entry = customtkinter.CTkEntry(
            dialog,
            textvariable=password_var,
            show="*",
            font=scaled_fonts['text']
        )
        entry.pack(pady=10, padx=20, fill="x")
        
        def submit():
            entered_password = password_var.get().strip()
            if verify_password(entered_password, settings['ui']['adminPassword']):
                dialog.destroy()
                callback(True)
            else:
                # Show error message
                error_dialog = customtkinter.CTkToplevel(parent)
                error_dialog.title("Error")
                error_dialog.transient(parent)
                
                # Set size and position
                width = 300
                height = 150
                x = (error_dialog.winfo_screenwidth() - width) // 2
                y = (error_dialog.winfo_screenheight() - height) // 2
                error_dialog.geometry(f"{width}x{height}+{x}+{y}")
                
                # Add message and button
                customtkinter.CTkLabel(
                    error_dialog,
                    text="Invalid password",
                    font=scaled_fonts['text']
                ).pack(pady=20)
                
                def close_error():
                    error_dialog.destroy()
                    dialog.destroy()
                    callback(False)
                
                customtkinter.CTkButton(
                    error_dialog,
                    text="OK",
                    command=close_error,
                    font=scaled_fonts['button']
                ).pack(pady=10)
                
                error_dialog.grab_set()
                callback(False)
        
        # Add submit button with improved formatting
        submit_button = customtkinter.CTkButton(
            dialog,
            text="Submit",
            command=submit,
            font=scaled_fonts['button'],
        ).pack(pady=10)
        
        # Bind Enter key
        entry.bind("<Return>", lambda e: submit())
        
        # Ensure focus
        entry.focus_set()
        entry.focus_force()
            
    except Exception as e:
        logger.error(f"Failed to show admin login dialog: {e}")
        callback(False)

class AdminPanel(customtkinter.CTkToplevel):
    """Windows admin panel implementation"""
    
    def __init__(self, parent, settings_manager):
        """Initialize the admin panel
        
        Args:
            parent: Parent window
            settings_manager: Settings manager instance
        """
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.settings = settings_manager.get_settings()
        
        # Set up UI
        self.title("Admin Control Panel")
        self.setup_ui()
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        
        # Load current settings
        self.load_current_settings()

    def setup_ui(self):
        """Set up the admin panel UI"""
        # Create main container
        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabview
        self.tabview = customtkinter.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True)
        
        # Create tabs
        self.create_soap_tab()
        self.create_storage_tab()
        self.create_system_tab()

    def create_soap_tab(self):
        """Create SOAP settings tab"""
        tab = self.tabview.add("SOAP Settings")
        
        # Client ID
        customtkinter.CTkLabel(tab, text="Client ID:").pack(pady=(10, 0))
        self.client_id_var = customtkinter.StringVar()
        customtkinter.CTkEntry(tab, textvariable=self.client_id_var).pack()
        
        # Username
        customtkinter.CTkLabel(tab, text="Username:").pack(pady=(10, 0))
        self.username_var = customtkinter.StringVar()
        customtkinter.CTkEntry(tab, textvariable=self.username_var).pack()
        
        # Password
        customtkinter.CTkLabel(tab, text="Password:").pack(pady=(10, 0))
        self.password_var = customtkinter.StringVar()
        customtkinter.CTkEntry(tab, textvariable=self.password_var).pack()

    def create_storage_tab(self):
        """Create storage settings tab"""
        tab = self.tabview.add("Storage")
        
        # Retention days
        customtkinter.CTkLabel(tab, text="Retention Days:").pack(pady=(10, 0))
        self.retention_var = customtkinter.StringVar()
        customtkinter.CTkEntry(tab, textvariable=self.retention_var).pack()
        
        # Max offline records
        customtkinter.CTkLabel(tab, text="Max Offline Records:").pack(pady=(10, 0))
        self.max_records_var = customtkinter.StringVar()
        customtkinter.CTkEntry(tab, textvariable=self.max_records_var).pack()

    def create_system_tab(self):
        """Create system tab"""
        tab = self.tabview.add("System")
        
        # Add close button
        customtkinter.CTkButton(
            tab,
            text="Close Application",
            command=self.close_application,
            fg_color="#FF3B30",
            hover_color="#CC2F26"
        ).pack(pady=10)

    def load_current_settings(self):
        """Load current settings into UI"""
        # SOAP settings
        self.client_id_var.set(str(self.settings['soap']['clientId']))
        self.username_var.set(self.settings['soap']['username'])
        self.password_var.set(self.settings['soap']['password'])
        
        # Storage settings
        self.retention_var.set(str(self.settings['storage']['retentionDays']))
        self.max_records_var.set(str(self.settings['storage']['maxOfflineRecords']))

    def save_settings(self):
        """Save settings"""
        try:
            # Update settings
            self.settings['soap']['clientId'] = int(self.client_id_var.get())
            self.settings['soap']['username'] = self.username_var.get()
            self.settings['soap']['password'] = self.password_var.get()
            
            self.settings['storage']['retentionDays'] = int(self.retention_var.get())
            self.settings['storage']['maxOfflineRecords'] = int(self.max_records_var.get())
            
            # Save settings
            self.settings_manager.save_settings(self.settings)
            
            # Close panel
            self.destroy()
            
        except ValueError as e:
            logger.error(f"Invalid setting value: {e}")
            self.show_error("Please check that all numeric values are valid numbers.")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self.show_error(f"Failed to save settings: {e}")

    def show_error(self, message: str):
        """Show error dialog"""
        dialog = customtkinter.CTkToplevel(self)
        dialog.title("Error")
        dialog.transient(self)
        
        customtkinter.CTkLabel(
            dialog,
            text=message,
            wraplength=300
        ).pack(pady=20)
        
        customtkinter.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy
        ).pack(pady=10)
        
        dialog.grab_set()

    def close_application(self):
        """Close the entire application"""
        self.master.quit()