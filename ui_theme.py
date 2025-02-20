import customtkinter
import os

def setup_theme():
    """Setup the MSI custom theme and dark mode"""
    # Set appearance mode to dark
    customtkinter.set_appearance_mode("dark")
    
    # Load custom theme
    theme_path = os.path.join("assets", "msi_theme.json")
    customtkinter.set_default_color_theme(theme_path)

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