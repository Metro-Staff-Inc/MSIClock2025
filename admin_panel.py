import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
import os
from typing import Callable, Dict, Any
from camera_service import CameraService

logger = logging.getLogger(__name__)

class AdminLoginDialog(tk.Toplevel):
    def __init__(self, parent, callback: Callable[[bool], None]):
        super().__init__(parent)
        self.callback = callback
        self.title("Admin Login")
        self.geometry("300x150")
        self.resizable(False, False)
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        self.password = tk.StringVar()
        self.create_widgets()
        
        # Handle window close button
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Password entry
        ttk.Label(main_frame, text="Enter Admin Password:").pack(pady=(0, 10))
        password_entry = ttk.Entry(main_frame, textvariable=self.password, show="*")
        password_entry.pack(fill=tk.X, pady=(0, 20))
        password_entry.focus()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Login", command=self.on_login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT)
        
        # Bind Enter key to login
        self.bind('<Return>', lambda e: self.on_login())

    def on_login(self):
        # Check against fixed admin password
        if self.password.get() == "Metro2024!":
            self.callback(True)
            self.destroy()
        else:
            messagebox.showerror("Error", "Invalid password")
            self.password.set("")

    def on_cancel(self):
        self.callback(False)
        self.destroy()

class AdminPanel(tk.Toplevel):
    def __init__(self, parent, settings_path: str = 'settings.json'):
        super().__init__(parent)
        self.settings_path = settings_path
        self.settings = self.load_settings()
        
        self.title("Admin Control Panel")
        self.geometry("800x600")
        self.minsize(800, 600)
        
        # Center on parent
        self.transient(parent)
        
        # Create custom styles
        style = ttk.Style()
        style.configure("Danger.TButton", foreground="red")
        
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
            messagebox.showerror("Error", f"Failed to load settings: {e}")
            return {}

    def create_widgets(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_settings_tab()
        self.create_camera_tab()
        self.create_logs_tab()
        self.create_system_tab()

    def create_settings_tab(self):
        settings_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(settings_frame, text="Settings")
        
        # SOAP Settings
        soap_frame = ttk.LabelFrame(settings_frame, text="SOAP Configuration", padding="10")
        soap_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Username
        ttk.Label(soap_frame, text="Username:").grid(row=0, column=0, sticky=tk.W)
        self.username_var = tk.StringVar()
        ttk.Entry(soap_frame, textvariable=self.username_var).grid(row=0, column=1, sticky=tk.EW, padx=5)
        
        # Password
        ttk.Label(soap_frame, text="Password:").grid(row=1, column=0, sticky=tk.W)
        self.password_var = tk.StringVar()
        ttk.Entry(soap_frame, textvariable=self.password_var, show="*").grid(row=1, column=1, sticky=tk.EW, padx=5)
        
        # Storage Settings
        storage_frame = ttk.LabelFrame(settings_frame, text="Storage Configuration", padding="10")
        storage_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Retention Days
        ttk.Label(storage_frame, text="Retention Days:").grid(row=0, column=0, sticky=tk.W)
        self.retention_var = tk.StringVar()
        ttk.Entry(storage_frame, textvariable=self.retention_var).grid(row=0, column=1, sticky=tk.EW, padx=5)
        
        # Save Button
        ttk.Button(settings_frame, text="Save Settings", command=self.save_settings).pack(pady=10)

    def create_camera_tab(self):
        camera_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(camera_frame, text="Camera")
        
        # Camera Settings
        settings_frame = ttk.LabelFrame(camera_frame, text="Camera Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Device ID
        ttk.Label(settings_frame, text="Device ID:").grid(row=0, column=0, sticky=tk.W)
        self.device_id_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.device_id_var).grid(row=0, column=1, sticky=tk.EW, padx=5)
        
        # Quality
        ttk.Label(settings_frame, text="Capture Quality:").grid(row=1, column=0, sticky=tk.W)
        self.quality_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.quality_var).grid(row=1, column=1, sticky=tk.EW, padx=5)
        
        # Test Camera Button
        ttk.Button(camera_frame, text="Test Camera", command=self.test_camera).pack(pady=10)

    def create_logs_tab(self):
        logs_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(logs_frame, text="Logs")
        
        # Log viewer
        self.log_text = tk.Text(logs_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = ttk.Frame(logs_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Refresh Logs", command=self.refresh_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT)

    def create_system_tab(self):
        system_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(system_frame, text="System")
        
        # System Information
        info_frame = ttk.LabelFrame(system_frame, text="System Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Version
        ttk.Label(info_frame, text="Version: 1.0.0").pack(anchor=tk.W)
        
        # Database Status
        db_frame = ttk.LabelFrame(system_frame, text="Database", padding="10")
        db_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(db_frame, text="Clean Old Records", command=self.clean_old_records).pack(anchor=tk.W)
        
        # Network Status
        net_frame = ttk.LabelFrame(system_frame, text="Network", padding="10")
        net_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(net_frame, text="Test Connection", command=self.test_connection).pack(anchor=tk.W)

        # Program Control
        control_frame = ttk.LabelFrame(system_frame, text="Program Control", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(control_frame, text="Close Program", command=self.close_program, style="Danger.TButton").pack(anchor=tk.W)

    def load_current_settings(self):
        # Load SOAP settings
        self.username_var.set(self.settings['soap']['username'])
        self.password_var.set(self.settings['soap']['password'])
        
        # Load storage settings
        self.retention_var.set(str(self.settings['storage']['retentionDays']))
        
        # Load camera settings
        self.device_id_var.set(str(self.settings['camera']['deviceId']))
        self.quality_var.set(str(self.settings['camera']['captureQuality']))

    def save_settings(self):
        try:
            # Update settings dictionary
            self.settings['soap']['username'] = self.username_var.get()
            self.settings['soap']['password'] = self.password_var.get()
            self.settings['storage']['retentionDays'] = int(self.retention_var.get())
            self.settings['camera']['deviceId'] = int(self.device_id_var.get())
            self.settings['camera']['captureQuality'] = int(self.quality_var.get())
            
            # Save to file
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            messagebox.showinfo("Success", "Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def test_camera(self):
        try:
            camera_service = CameraService(self.settings_path)
            results = camera_service.test_camera()
            
            message = "Camera Test Results:\n\n"
            for key, value in results.items():
                message += f"{key}: {value}\n"
            
            messagebox.showinfo("Camera Test", message)
            
        except Exception as e:
            logger.error(f"Camera test failed: {e}")
            messagebox.showerror("Error", f"Camera test failed: {e}")

    def refresh_logs(self):
        try:
            self.log_text.delete(1.0, tk.END)
            
            if os.path.exists('app.log'):
                with open('app.log', 'r') as f:
                    self.log_text.insert(tk.END, f.read())
                    
        except Exception as e:
            logger.error(f"Failed to refresh logs: {e}")
            messagebox.showerror("Error", f"Failed to refresh logs: {e}")

    def clear_logs(self):
        try:
            if os.path.exists('app.log'):
                with open('app.log', 'w') as f:
                    f.write('')
            self.log_text.delete(1.0, tk.END)
            messagebox.showinfo("Success", "Logs cleared successfully")
            
        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
            messagebox.showerror("Error", f"Failed to clear logs: {e}")

    def clean_old_records(self):
        # TODO: Implement database cleanup
        messagebox.showinfo("Info", "Database cleanup not implemented yet")

    def test_connection(self):
        # TODO: Implement connection test
        messagebox.showinfo("Info", "Connection test not implemented yet")

    def on_close(self):
        self.destroy()

    def close_program(self):
        if messagebox.askyesno("Confirm Close", "Are you sure you want to close the program?"):
            self.master.quit()

if __name__ == "__main__":
    # Test admin panel
    root = tk.Tk()
    root.withdraw()
    
    def on_login(success: bool):
        if success:
            AdminPanel(root)
    
    AdminLoginDialog(root, on_login)
    root.mainloop()