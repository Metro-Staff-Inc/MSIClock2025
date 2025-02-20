import customtkinter
import json
import logging
import os
from typing import Callable, Dict, Any
from camera_service import CameraService
from ui_theme import StatusColors

logger = logging.getLogger(__name__)

def show_admin_login(parent, callback: Callable[[bool], None]):
    """Show admin login dialog and call callback with result"""
    try:
        # Load settings
        with open('settings.json', 'r') as f:
            settings = json.load(f)
            
        # Create and show input dialog
        dialog = customtkinter.CTkInputDialog(
            text="Enter Admin Password:",
            title="Admin Login"
        )
        
        # Center on screen
        dialog.lift()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 300) // 2
        y = (dialog.winfo_screenheight() - 150) // 2
        dialog.geometry(f"+{x}+{y}")
        
        password = dialog.get_input()
        
        # Check password (handle cancel case)
        if password is None:
            callback(False)
            return
            
        if password == settings['ui']['adminPassword']:
            callback(True)
        else:
            customtkinter.CTkMessagebox(
                title="Error",
                message="Invalid password",
                icon="cancel"
            )
            callback(False)
            
    except Exception as e:
        logger.error(f"Failed to show admin login dialog: {e}")
        callback(False)

class AdminPanel(customtkinter.CTkToplevel):
    def __init__(self, parent, settings_path: str = 'settings.json'):
        super().__init__(parent)
        self.settings_path = settings_path
        self.settings = self.load_settings()
        
        self.title("Admin Control Panel")
        self.geometry("800x600")
        self.minsize(800, 600)
        
        # Center on screen
        self.lift()  # Bring to front
        self.update_idletasks()  # Update geometry
        
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculate position
        window_width = 800
        window_height = 600
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set position
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        self.load_current_settings()
        
        # Handle window close button
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_settings(self) -> Dict[str, Any]:
        try:
            with open(self.settings_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            self.show_error(f"Failed to load settings: {e}")
            return {}

    def show_error(self, message: str):
        """Show error dialog"""
        dialog = customtkinter.CTkToplevel(self)
        dialog.title("Error")
        dialog.geometry("300x100")
        dialog.transient(self)
        dialog.grab_set()
        
        customtkinter.CTkLabel(dialog, text=message, wraplength=250).pack(pady=10)
        customtkinter.CTkButton(dialog, text="OK", command=dialog.destroy).pack()

    def create_widgets(self):
        # Create tabview for tabs
        self.tabview = customtkinter.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_settings_tab()
        self.create_camera_tab()
        self.create_logs_tab()
        self.create_system_tab()

    def create_settings_tab(self):
        settings_tab = self.tabview.add("Settings")
        
        # Create scrollable frame for entire content
        scrollable_frame = customtkinter.CTkScrollableFrame(settings_tab)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Content container
        content_frame = customtkinter.CTkFrame(scrollable_frame)
        content_frame.pack(fill="x", expand=True)
        
        # SOAP Settings
        soap_frame = customtkinter.CTkFrame(content_frame)
        soap_frame.pack(fill="x", pady=(0, 20))
        
        customtkinter.CTkLabel(soap_frame, text="SOAP Configuration", font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=5)
        
        # Client ID
        customtkinter.CTkLabel(soap_frame, text="Client ID:").pack(anchor="w", padx=10)
        self.client_id_var = customtkinter.StringVar()
        customtkinter.CTkEntry(soap_frame, textvariable=self.client_id_var).pack(fill="x", padx=10, pady=(0, 10))
        
        # Username
        customtkinter.CTkLabel(soap_frame, text="Username:").pack(anchor="w", padx=10)
        self.username_var = customtkinter.StringVar()
        customtkinter.CTkEntry(soap_frame, textvariable=self.username_var).pack(fill="x", padx=10, pady=(0, 10))
        
        # SOAP Password (always visible)
        customtkinter.CTkLabel(soap_frame, text="Password:").pack(anchor="w", padx=10)
        self.password_var = customtkinter.StringVar()
        self.password_entry = customtkinter.CTkEntry(soap_frame, textvariable=self.password_var)
        self.password_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # Admin Settings
        admin_frame = customtkinter.CTkFrame(content_frame)
        admin_frame.pack(fill="x", pady=(0, 20))
        
        customtkinter.CTkLabel(admin_frame, text="Admin Configuration", font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=5)
        
        # New Admin Password with toggle
        customtkinter.CTkLabel(admin_frame, text="New Password:").pack(anchor="w", padx=10)
        new_pass_frame = customtkinter.CTkFrame(admin_frame, fg_color="transparent")
        new_pass_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.new_password_var = customtkinter.StringVar()
        self.new_password_entry = customtkinter.CTkEntry(new_pass_frame, textvariable=self.new_password_var, show="*")
        self.new_password_entry.pack(side="left", fill="x", expand=True)
        
        def toggle_new_password():
            if self.new_password_entry.cget('show') == '':
                self.new_password_entry.configure(show='*')
            else:
                self.new_password_entry.configure(show='')
        
        new_toggle_btn = customtkinter.CTkButton(
            new_pass_frame,
            text="👁",
            width=30,
            command=toggle_new_password
        )
        new_toggle_btn.pack(side="left", padx=(5, 0))
        
        # Confirm Admin Password with toggle
        customtkinter.CTkLabel(admin_frame, text="Confirm Password:").pack(anchor="w", padx=10)
        confirm_pass_frame = customtkinter.CTkFrame(admin_frame, fg_color="transparent")
        confirm_pass_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.confirm_password_var = customtkinter.StringVar()
        self.confirm_password_entry = customtkinter.CTkEntry(confirm_pass_frame, textvariable=self.confirm_password_var, show="*")
        self.confirm_password_entry.pack(side="left", fill="x", expand=True)
        
        def toggle_confirm_password():
            if self.confirm_password_entry.cget('show') == '':
                self.confirm_password_entry.configure(show='*')
            else:
                self.confirm_password_entry.configure(show='')
        
        confirm_toggle_btn = customtkinter.CTkButton(
            confirm_pass_frame,
            text="👁",
            width=30,
            command=toggle_confirm_password
        )
        confirm_toggle_btn.pack(side="left", padx=(5, 0))
        
        # Storage Settings
        storage_frame = customtkinter.CTkFrame(content_frame)
        storage_frame.pack(fill="x", pady=(0, 20))
        
        customtkinter.CTkLabel(storage_frame, text="Storage Configuration", font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=5)
        
        # Retention Days
        customtkinter.CTkLabel(storage_frame, text="Retention Days:").pack(anchor="w", padx=10)
        self.retention_var = customtkinter.StringVar()
        customtkinter.CTkEntry(storage_frame, textvariable=self.retention_var).pack(fill="x", padx=10, pady=(0, 10))
        
        # Add some padding at the bottom of content
        customtkinter.CTkFrame(content_frame, height=20).pack(fill="x")
        
        # Create a frame for the save button that stays at the bottom of the tab
        save_frame = customtkinter.CTkFrame(settings_tab)
        save_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        # Save Button with theme colors
        save_button = customtkinter.CTkButton(
            save_frame,
            text="Save Settings",
            command=self.save_settings,
            fg_color="#A4D233",
            hover_color="#8AB22B",
            height=40,
            font=("Arial", 14, "bold"),
            text_color="#000000"  # Theme uses black text on buttons
        )
        save_button.pack(fill="x")

    def create_camera_tab(self):
        camera_tab = self.tabview.add("Camera")
        
        # Camera Settings
        settings_frame = customtkinter.CTkFrame(camera_tab)
        settings_frame.pack(fill="x", pady=(0, 10))
        
        customtkinter.CTkLabel(settings_frame, text="Camera Settings", font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=5)
        
        # Device ID
        customtkinter.CTkLabel(settings_frame, text="Device ID:").pack(anchor="w", padx=10)
        self.device_id_var = customtkinter.StringVar()
        customtkinter.CTkEntry(settings_frame, textvariable=self.device_id_var).pack(fill="x", padx=10, pady=(0, 10))
        
        # Quality
        customtkinter.CTkLabel(settings_frame, text="Capture Quality:").pack(anchor="w", padx=10)
        self.quality_var = customtkinter.StringVar()
        customtkinter.CTkEntry(settings_frame, textvariable=self.quality_var).pack(fill="x", padx=10, pady=(0, 10))
        
        # Test Camera Button
        customtkinter.CTkButton(camera_tab, text="Test Camera", command=self.test_camera).pack(pady=10)

    def create_logs_tab(self):
        logs_tab = self.tabview.add("Logs")
        
        # Create main container
        main_container = customtkinter.CTkFrame(logs_tab)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Log viewer with increased height
        self.log_text = customtkinter.CTkTextbox(main_container, wrap="word", height=400)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=(5, 10))
        
        # Buttons with better styling
        button_frame = customtkinter.CTkFrame(main_container)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        customtkinter.CTkButton(
            button_frame,
            text="Refresh Logs",
            command=self.refresh_logs,
            height=35,
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            button_frame,
            text="Clear Logs",
            command=self.clear_logs,
            height=35,
            font=("Arial", 12, "bold"),
            fg_color="#A4D233",
            hover_color="#8AB22B",
            text_color="#000000"
        ).pack(side="left", padx=5)
        
        # Initial load of logs
        self.refresh_logs()
        
        # Setup auto-refresh every 5 seconds
        self.after(5000, self.auto_refresh_logs)
        
    def auto_refresh_logs(self):
        """Auto refresh logs if the logs tab is visible"""
        try:
            if self.tabview.get() == "Logs":
                self.refresh_logs()
        finally:
            # Reschedule refresh
            self.after(5000, self.auto_refresh_logs)

    def create_system_tab(self):
        system_tab = self.tabview.add("System")
        
        # System Information
        info_frame = customtkinter.CTkFrame(system_tab)
        info_frame.pack(fill="x", pady=(0, 10))
        
        customtkinter.CTkLabel(info_frame, text="System Information", font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=5)
        customtkinter.CTkLabel(info_frame, text="Version: 1.0.0").pack(anchor="w", padx=10, pady=5)
        
        # Database Status
        db_frame = customtkinter.CTkFrame(system_tab)
        db_frame.pack(fill="x", pady=(0, 10))
        
        customtkinter.CTkLabel(db_frame, text="Database", font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=5)
        customtkinter.CTkButton(db_frame, text="Clean Old Records", command=self.clean_old_records).pack(anchor="w", padx=10, pady=5)
        
        # Network Status
        net_frame = customtkinter.CTkFrame(system_tab)
        net_frame.pack(fill="x", pady=(0, 10))
        
        customtkinter.CTkLabel(net_frame, text="Network", font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=5)
        customtkinter.CTkButton(net_frame, text="Test Connection", command=self.test_connection).pack(anchor="w", padx=10, pady=5)
        
        # Program Control
        control_frame = customtkinter.CTkFrame(system_tab)
        control_frame.pack(fill="x", pady=(0, 10))
        
        customtkinter.CTkLabel(control_frame, text="Program Control", font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=5)
        customtkinter.CTkButton(control_frame, text="Close Program", 
                              command=self.close_program,
                              fg_color=StatusColors.ERROR,
                              hover_color="#CC2F26").pack(anchor="w", padx=10, pady=5)

    def load_current_settings(self):
        # Load admin settings
        self.new_password_var.set("")
        self.confirm_password_var.set("")

        # Load SOAP settings
        self.client_id_var.set(str(self.settings['soap']['clientId']))
        self.username_var.set(self.settings['soap']['username'])
        self.password_var.set(self.settings['soap']['password'])
        
        # Load storage settings
        self.retention_var.set(str(self.settings['storage']['retentionDays']))
        
        # Load camera settings
        self.device_id_var.set(str(self.settings['camera']['deviceId']))
        self.quality_var.set(str(self.settings['camera']['captureQuality']))

    def save_settings(self):
        try:
            # Validate admin password change
            new_password = self.new_password_var.get()
            confirm_password = self.confirm_password_var.get()
            
            if new_password or confirm_password:  # Only validate if either field has content
                if new_password != confirm_password:
                    self.show_error("New password and confirm password do not match")
                    return
                self.settings['ui']['adminPassword'] = new_password

            # SOAP settings
            self.settings['soap']['clientId'] = int(self.client_id_var.get())
            self.settings['soap']['username'] = self.username_var.get()
            self.settings['soap']['password'] = self.password_var.get()
            self.settings['storage']['retentionDays'] = int(self.retention_var.get())
            self.settings['camera']['deviceId'] = int(self.device_id_var.get())
            self.settings['camera']['captureQuality'] = int(self.quality_var.get())
            
            # Save to file
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            dialog = customtkinter.CTkToplevel(self)
            dialog.title("Success")
            dialog.geometry("200x100")
            dialog.transient(self)
            dialog.grab_set()
            
            customtkinter.CTkLabel(dialog, text="Settings saved successfully").pack(pady=10)
            customtkinter.CTkButton(dialog, text="OK", command=dialog.destroy).pack()
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self.show_error(f"Failed to save settings: {e}")

    def test_camera(self):
        try:
            camera_service = CameraService(self.settings_path)
            results = camera_service.test_camera()
            
            dialog = customtkinter.CTkToplevel(self)
            dialog.title("Camera Test")
            dialog.geometry("300x200")
            dialog.transient(self)
            dialog.grab_set()
            
            message = "Camera Test Results:\n\n"
            for key, value in results.items():
                message += f"{key}: {value}\n"
            
            customtkinter.CTkLabel(dialog, text=message, wraplength=250).pack(pady=10)
            customtkinter.CTkButton(dialog, text="OK", command=dialog.destroy).pack()
            
        except Exception as e:
            logger.error(f"Camera test failed: {e}")
            self.show_error(f"Camera test failed: {e}")

    def refresh_logs(self):
        try:
            self.log_text.delete("1.0", "end")
            
            log_path = os.path.join('logs', 'app.log')
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    self.log_text.insert("1.0", f.read())
            else:
                self.log_text.insert("1.0", "No logs found")
                    
        except Exception as e:
            logger.error(f"Failed to refresh logs: {e}")
            self.show_error(f"Failed to refresh logs: {e}")

    def clear_logs(self):
        try:
            log_path = os.path.join('logs', 'app.log')
            if os.path.exists(log_path):
                with open(log_path, 'w') as f:
                    f.write('')
            self.log_text.delete("1.0", "end")
            self.log_text.insert("1.0", "Logs cleared")
            
            dialog = customtkinter.CTkToplevel(self)
            dialog.title("Success")
            dialog.geometry("200x100")
            dialog.transient(self)
            dialog.grab_set()
            
            customtkinter.CTkLabel(dialog, text="Logs cleared successfully").pack(pady=10)
            customtkinter.CTkButton(dialog, text="OK", command=dialog.destroy).pack()
            
        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
            self.show_error(f"Failed to clear logs: {e}")

    def clean_old_records(self):
        # TODO: Implement database cleanup
        self.show_error("Database cleanup not implemented yet")

    def test_connection(self):
        # TODO: Implement connection test
        self.show_error("Connection test not implemented yet")

    def on_close(self):
        self.destroy()

    def close_program(self):
        dialog = customtkinter.CTkToplevel(self)
        dialog.title("Confirm Close")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog on screen
        dialog.lift()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 300) // 2
        y = (dialog.winfo_screenheight() - 150) // 2
        dialog.geometry(f"+{x}+{y}")
        
        customtkinter.CTkLabel(dialog, text="Are you sure you want to close the program?", 
                             wraplength=250).pack(pady=10)
        
        button_frame = customtkinter.CTkFrame(dialog)
        button_frame.pack(fill="x", padx=20)
        
        customtkinter.CTkButton(button_frame, text="Yes", 
                              command=lambda: [dialog.destroy(), self.master.quit()],
                              fg_color=StatusColors.ERROR,
                              hover_color="#CC2F26").pack(side="left", padx=5)
        customtkinter.CTkButton(button_frame, text="No", 
                              command=dialog.destroy).pack(side="left")

if __name__ == "__main__":
    # Test admin panel
    root = customtkinter.CTk()
    root.withdraw()
    
    def on_login(success: bool):
        if success:
            AdminPanel(root)
    
    show_admin_login(root, on_login)
    root.mainloop()
