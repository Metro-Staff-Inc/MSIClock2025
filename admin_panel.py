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
            
        # Create dialog window
        dialog = customtkinter.CTkToplevel(parent)
        dialog.title("Admin Login")
        dialog.attributes('-topmost', True)
        
        # Scale dialog size
        width = 300
        height = 150
        
        # Center on screen
        x = (dialog.winfo_screenwidth() - width) // 2
        y = (dialog.winfo_screenheight() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make it modal and ensure proper window management
        dialog.transient(parent)
        dialog.update_idletasks()
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
            if entered_password == settings['ui']['adminPassword']:
                dialog.destroy()
                callback(True)
            else:
                # Show error message
                error_dialog = customtkinter.CTkToplevel(parent)
                error_dialog.title("Error")
                error_dialog.attributes('-topmost', True)
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
        
        # Add submit button
        customtkinter.CTkButton(
            dialog,
            text="Submit",
            command=submit,
            font=scaled_fonts['button']
        ).pack(pady=(10, 20))
        
        # Focus the entry
        entry.focus_set()
        
        # Bind Enter key and focus
        entry.bind("<Return>", lambda e: submit())
        entry.focus_set()
            
    except Exception as e:
        logger.error(f"Failed to show admin login dialog: {e}")
        callback(False)

class AdminPanel(customtkinter.CTkToplevel):
    def __init__(self, parent, settings_path: str = 'settings.json'):
        super().__init__(parent)
        self.settings_path = settings_path
        self.settings = self.load_settings()
        
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculate scaled dimensions
        base_width = 800
        base_height = 600
        window_width = 700
        window_height = 500
        
        self.title("Admin Control Panel")
        
        # Set initial size to match content
        self.geometry(f"{window_width}x{window_height}")
        
        # Update to ensure window is created
        self.update_idletasks()
        
        # Set minimum size after window is created
        self.minsize(window_width, window_height)
        
        # Center on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Bring to front
        self.lift()
        
        # Create scaled fonts dictionary
        self.scaled_fonts = {
            'title': ('Roboto', 14, 'bold'),
            'text': ('Roboto', 12),
            'button': ('Roboto', 12, 'bold')
        }
        
        # Make it modal and ensure proper window management
        self.transient(parent)
        self.attributes('-topmost', True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Ensure window is ready before grabbing focus
        self.update_idletasks()
        self.grab_set()
        self.focus_force()
        
        # Keep window on top
        self.lift()
        parent.lift(self)  # Ensure admin panel stays above parent
        
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
        
        # Scale dialog dimensions
        width = 300
        height = 100
        dialog.geometry(f"{width}x{height}")
        dialog.transient(self)
        dialog.grab_set()
        
        customtkinter.CTkLabel(
            dialog,
            text=message,
            wraplength=250,
            font=self.scaled_fonts['text']
        ).pack(pady=10)
        
        customtkinter.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy,
            font=self.scaled_fonts['button'],
            height=30
        ).pack()

    def create_widgets(self):
        # Create main container frame
        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True)
        
        # Create tabview for tabs
        self.tabview = customtkinter.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_settings_tab()
        self.create_camera_tab()
        self.create_logs_tab()
        self.create_system_tab()

    def create_settings_tab(self):
        settings_tab = self.tabview.add("Settings")
        
        # Configure grid weights for settings tab
        settings_tab.grid_columnconfigure(0, weight=1)
        settings_tab.grid_rowconfigure(0, weight=1)
        
        # Create scrollable frame for entire content
        scrollable_frame = customtkinter.CTkScrollableFrame(settings_tab)
        scrollable_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Configure grid weights for scrollable frame
        scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # Content container
        content_frame = customtkinter.CTkFrame(scrollable_frame)
        content_frame.grid(row=0, column=0, sticky="ew")
        content_frame.grid_columnconfigure(0, weight=1)
        
        current_row = 0
        
        # SOAP Settings
        soap_frame = customtkinter.CTkFrame(content_frame)
        soap_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 20))
        soap_frame.grid_columnconfigure(0, weight=1)
        
        soap_row = 0
        customtkinter.CTkLabel(soap_frame, text="SOAP Configuration", font=self.scaled_fonts['title']).grid(row=soap_row, column=0, sticky="w", padx=10, pady=5)
        
        # Client ID
        soap_row += 1
        customtkinter.CTkLabel(soap_frame, text="Client ID:", font=self.scaled_fonts['text']).grid(row=soap_row, column=0, sticky="w", padx=10)
        soap_row += 1
        self.client_id_var = customtkinter.StringVar()
        customtkinter.CTkEntry(soap_frame, textvariable=self.client_id_var, font=self.scaled_fonts['text']).grid(row=soap_row, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Username
        soap_row += 1
        customtkinter.CTkLabel(soap_frame, text="Username:", font=self.scaled_fonts['text']).grid(row=soap_row, column=0, sticky="w", padx=10)
        soap_row += 1
        self.username_var = customtkinter.StringVar()
        customtkinter.CTkEntry(soap_frame, textvariable=self.username_var, font=self.scaled_fonts['text']).grid(row=soap_row, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # SOAP Password
        soap_row += 1
        customtkinter.CTkLabel(soap_frame, text="Password:", font=self.scaled_fonts['text']).grid(row=soap_row, column=0, sticky="w", padx=10)
        soap_row += 1
        self.password_var = customtkinter.StringVar()
        self.password_entry = customtkinter.CTkEntry(soap_frame, textvariable=self.password_var, font=self.scaled_fonts['text'])
        self.password_entry.grid(row=soap_row, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Admin Settings
        current_row += 1
        admin_frame = customtkinter.CTkFrame(content_frame)
        admin_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 20))
        admin_frame.grid_columnconfigure(1, weight=1)  # Column 1 will contain the entry fields
        
        admin_row = 0
        customtkinter.CTkLabel(admin_frame, text="Admin Configuration", font=self.scaled_fonts['title']).grid(row=admin_row, column=0, columnspan=3, sticky="w", padx=10, pady=5)
        
        # New Admin Password with toggle
        admin_row += 1
        customtkinter.CTkLabel(admin_frame, text="New Password:", font=self.scaled_fonts['text']).grid(row=admin_row, column=0, sticky="w", padx=10)
        self.new_password_var = customtkinter.StringVar()
        self.new_password_entry = customtkinter.CTkEntry(admin_frame, textvariable=self.new_password_var, show="*", font=self.scaled_fonts['text'])
        self.new_password_entry.grid(row=admin_row, column=1, sticky="ew", padx=10, pady=(0, 10))
        
        def toggle_new_password():
            if self.new_password_entry.cget('show') == '':
                self.new_password_entry.configure(show='*')
            else:
                self.new_password_entry.configure(show='')
        
        new_toggle_btn = customtkinter.CTkButton(
            admin_frame,
            text="👁",
            width=30,
            command=toggle_new_password
        )
        new_toggle_btn.grid(row=admin_row, column=2, padx=(0, 10))
        
        # Confirm Admin Password with toggle
        admin_row += 1
        customtkinter.CTkLabel(admin_frame, text="Confirm Password:", font=self.scaled_fonts['text']).grid(row=admin_row, column=0, sticky="w", padx=10)
        self.confirm_password_var = customtkinter.StringVar()
        self.confirm_password_entry = customtkinter.CTkEntry(admin_frame, textvariable=self.confirm_password_var, show="*", font=self.scaled_fonts['text'])
        self.confirm_password_entry.grid(row=admin_row, column=1, sticky="ew", padx=10, pady=(0, 10))
        
        def toggle_confirm_password():
            if self.confirm_password_entry.cget('show') == '':
                self.confirm_password_entry.configure(show='*')
            else:
                self.confirm_password_entry.configure(show='')
        
        confirm_toggle_btn = customtkinter.CTkButton(
            admin_frame,
            text="👁",
            width=30,
            command=toggle_confirm_password,
            font=self.scaled_fonts['text']
        )
        confirm_toggle_btn.grid(row=admin_row, column=2, padx=(0, 10))
        
        # Storage Settings
        current_row += 1
        storage_frame = customtkinter.CTkFrame(content_frame)
        storage_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 20))
        storage_frame.grid_columnconfigure(1, weight=1)
        
        storage_row = 0
        customtkinter.CTkLabel(storage_frame, text="Storage Configuration", font=self.scaled_fonts['title']).grid(row=storage_row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        
        # Retention Days
        storage_row += 1
        customtkinter.CTkLabel(storage_frame, text="Retention Days:", font=self.scaled_fonts['text']).grid(row=storage_row, column=0, sticky="w", padx=10)
        self.retention_var = customtkinter.StringVar()
        customtkinter.CTkEntry(storage_frame, textvariable=self.retention_var, font=self.scaled_fonts['text']).grid(row=storage_row, column=1, sticky="ew", padx=10, pady=(0, 10))
        
        # Add some padding at the bottom of content
        current_row += 1
        customtkinter.CTkFrame(content_frame, height=20).grid(row=current_row, column=0, sticky="ew")
        
        # Create a frame for the save button that stays at the bottom of the tab
        save_frame = customtkinter.CTkFrame(settings_tab)
        save_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        save_frame.grid_columnconfigure(0, weight=1)
        
        # Save Button with theme colors
        save_button = customtkinter.CTkButton(
            save_frame,
            text="Save Settings",
            command=self.save_settings,
            fg_color="#A4D233",
            hover_color="#8AB22B",
            height=40,  # Scale button height
            font=self.scaled_fonts['button'],
            text_color="#000000"  # Theme uses black text on buttons
        )
        save_button.grid(row=0, column=0, sticky="ew", padx=(10, 5))

    def create_camera_tab(self):
        camera_tab = self.tabview.add("Camera")
        
        # Configure grid weights for camera tab
        camera_tab.grid_columnconfigure(0, weight=1)
        
        # Camera Settings
        settings_frame = customtkinter.CTkFrame(camera_tab)
        settings_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        settings_frame.grid_columnconfigure(1, weight=1)  # Column for entry fields
        
        current_row = 0
        customtkinter.CTkLabel(settings_frame, text="Camera Settings", font=self.scaled_fonts['title']).grid(row=current_row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        
        # Device ID
        current_row += 1
        customtkinter.CTkLabel(settings_frame, text="Device ID:", font=self.scaled_fonts['text']).grid(row=current_row, column=0, sticky="w", padx=10)
        self.device_id_var = customtkinter.StringVar()
        customtkinter.CTkEntry(settings_frame, textvariable=self.device_id_var, font=self.scaled_fonts['text']).grid(row=current_row, column=1, sticky="ew", padx=10, pady=(0, 10))
        
        # Quality
        current_row += 1
        customtkinter.CTkLabel(settings_frame, text="Capture Quality:", font=self.scaled_fonts['text']).grid(row=current_row, column=0, sticky="w", padx=10)
        self.quality_var = customtkinter.StringVar()
        customtkinter.CTkEntry(settings_frame, textvariable=self.quality_var, font=self.scaled_fonts['text']).grid(row=current_row, column=1, sticky="ew", padx=10, pady=(0, 10))
        
        # Test Camera Button
        test_button = customtkinter.CTkButton(
            camera_tab,
            text="Test Camera",
            command=self.test_camera,
            font=self.scaled_fonts['button'],
            height=35
        )
        test_button.grid(row=1, column=0, pady=10)

    def create_logs_tab(self):
        logs_tab = self.tabview.add("Logs")
        
        # Configure grid weights for logs tab
        logs_tab.grid_columnconfigure(0, weight=1)
        logs_tab.grid_rowconfigure(0, weight=1)
        
        # Create main container
        main_container = customtkinter.CTkFrame(logs_tab)
        main_container.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Configure grid weights for main container
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # Log viewer with increased height and scaled dimensions
        scaled_height = 400
        self.log_text = customtkinter.CTkTextbox(
            main_container,
            wrap="word",
            height=scaled_height,
            font=self.scaled_fonts['text']
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 10))
        
        # Buttons with better styling
        button_frame = customtkinter.CTkFrame(main_container)
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        button_frame.grid_columnconfigure((2, 3), weight=1)  # Add weight to columns after buttons
        
        customtkinter.CTkButton(
            button_frame,
            text="Refresh Logs",
            command=self.refresh_logs,
            height=35,
            font=self.scaled_fonts['button']
        ).grid(row=0, column=0, padx=5)
        
        customtkinter.CTkButton(
            button_frame,
            text="Clear Logs",
            command=self.clear_logs,
            height=35,
            font=self.scaled_fonts['button'],
            fg_color="#A4D233",
            hover_color="#8AB22B",
            text_color="#000000"
        ).grid(row=0, column=1, padx=5)
        
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
        
        # Configure grid weights for system tab
        system_tab.grid_columnconfigure(0, weight=1)
        
        current_row = 0
        
        # System Information
        info_frame = customtkinter.CTkFrame(system_tab)
        info_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 10))
        info_frame.grid_columnconfigure(0, weight=1)
        
        info_row = 0
        customtkinter.CTkLabel(info_frame, text="System Information", font=self.scaled_fonts['title']).grid(row=info_row, column=0, sticky="w", padx=10, pady=5)
        info_row += 1
        customtkinter.CTkLabel(info_frame, text="Version: 1.0.0", font=self.scaled_fonts['text']).grid(row=info_row, column=0, sticky="w", padx=10, pady=5)
        
        # Database Status
        current_row += 1
        db_frame = customtkinter.CTkFrame(system_tab)
        db_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 10))
        db_frame.grid_columnconfigure(0, weight=1)
        
        db_row = 0
        customtkinter.CTkLabel(db_frame, text="Database", font=self.scaled_fonts['title']).grid(row=db_row, column=0, sticky="w", padx=10, pady=5)
        db_row += 1
        customtkinter.CTkButton(
            db_frame,
            text="Clean Old Records",
            command=self.clean_old_records,
            font=self.scaled_fonts['button'],
            height=35
        ).grid(row=db_row, column=0, sticky="w", padx=10, pady=5)
        
        # Network Status
        current_row += 1
        net_frame = customtkinter.CTkFrame(system_tab)
        net_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 10))
        net_frame.grid_columnconfigure(0, weight=1)
        
        net_row = 0
        customtkinter.CTkLabel(net_frame, text="Network", font=self.scaled_fonts['title']).grid(row=net_row, column=0, sticky="w", padx=10, pady=5)
        net_row += 1
        customtkinter.CTkButton(
            net_frame,
            text="Test Connection",
            command=self.test_connection,
            font=self.scaled_fonts['button'],
            height=35
        ).grid(row=net_row, column=0, sticky="w", padx=10, pady=5)
        
        # Program Control
        current_row += 1
        control_frame = customtkinter.CTkFrame(system_tab)
        control_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 10))
        control_frame.grid_columnconfigure(0, weight=1)
        
        control_row = 0
        customtkinter.CTkLabel(control_frame, text="Program Control", font=self.scaled_fonts['title']).grid(row=control_row, column=0, sticky="w", padx=10, pady=5)
        control_row += 1
        customtkinter.CTkButton(
            control_frame,
            text="Close Program",
            command=self.close_program,
            fg_color=StatusColors.ERROR,
            hover_color="#CC2F26",
            font=self.scaled_fonts['button'],
            height=35
        ).grid(row=control_row, column=0, sticky="w", padx=10, pady=5)

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
        
        customtkinter.CTkLabel(dialog, text="Are you sure you want to close the program?", wraplength=250).pack(pady=10)
        
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
