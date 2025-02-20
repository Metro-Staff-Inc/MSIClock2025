import customtkinter
import os
import platform

def setup_theme():
    """Setup the MSI custom theme and dark mode"""
    # Set appearance mode to dark
    customtkinter.set_appearance_mode("dark")
    
    # Load custom theme
    theme_path = os.path.join("assets", "msi_theme.json")
    customtkinter.set_default_color_theme(theme_path)
    
    # Register fonts if on Linux
    if platform.system() == "Linux":
        try:
            import subprocess
            font_dir = os.path.expanduser("~/.fonts")
            os.makedirs(font_dir, exist_ok=True)
            
            # Copy fonts if not already present
            fonts = ["Roboto-Regular.ttf", "OpenSans-Regular.ttf"]
            for font in fonts:
                src = os.path.join("assets", "fonts", font)
                dst = os.path.join(font_dir, font)
                if os.path.exists(src) and not os.path.exists(dst):
                    import shutil
                    shutil.copy2(src, dst)
            
            # Update font cache
            subprocess.run(["fc-cache", "-f", "-v"], check=True)
        except Exception as e:
            print(f"Warning: Could not setup fonts: {e}")

# Color constants for status messages
class StatusColors:
    ERROR = "#FF3B30"
    SUCCESS = "#34C759"
    NORMAL = "#FFFFFF"
    INACTIVE = "gray60"
    
    @staticmethod
    def get_color(status_type: str) -> str:
        """Get color for different status types"""
        colors = {
            "error": StatusColors.ERROR,
            "success": StatusColors.SUCCESS,
            "normal": StatusColors.NORMAL,
            "inactive": StatusColors.INACTIVE
        }
        return colors.get(status_type.lower(), StatusColors.NORMAL)