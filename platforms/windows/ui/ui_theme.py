"""
Windows-specific UI theme setup for MSI Time Clock.
"""

import os
import customtkinter
import logging

logger = logging.getLogger(__name__)

def setup_theme():
    """Setup the MSI custom theme and dark mode for Windows"""
    # Set appearance mode to dark
    customtkinter.set_appearance_mode("dark")
    
    # Load custom theme
    theme_path = os.path.join("assets", "common", "msi_theme.json")
    customtkinter.set_default_color_theme(theme_path)
    
    # Register fonts
    try:
        # Windows fonts are in assets/windows/fonts
        font_dir = os.path.join("assets", "windows", "fonts")
        
        # Register each font
        fonts = [
            "IBMPlexSans-Medium.ttf",
            "IBMPlexSansCondensed-Bold.ttf",
            "Roboto-Regular.ttf"
        ]
        
        for font in fonts:
            font_path = os.path.join(font_dir, font)
            if os.path.exists(font_path):
                customtkinter.windows.widgets.font.CTkFont(font_path)
            else:
                logger.warning(f"Font file not found: {font_path}")
                
    except Exception as e:
        logger.error(f"Failed to setup fonts: {e}")

# Color constants for status messages
class StatusColors:
    """Color constants for status messages"""
    ERROR = "#FF3B30"
    SUCCESS = "#34C759"
    NORMAL = "#FFFFFF"
    INACTIVE = "gray60"
    WARNING = "#F39C12"