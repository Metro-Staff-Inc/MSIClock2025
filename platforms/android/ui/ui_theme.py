"""
Android-specific UI theme setup for MSI Time Clock.
Uses KivyMD for Material Design components.
"""

import os
import json
import logging
from kivy.core.text import LabelBase
from kivymd.app import MDApp
from kivy.core.window import Window
from kivy.metrics import dp

logger = logging.getLogger(__name__)

def setup_theme():
    """Setup the MSI custom theme for Android"""
    # Set window properties
    Window.softinput_mode = "below_target"  # Keep UI visible when keyboard is shown
    
    # Register fonts
    try:
        font_dir = os.path.join("assets", "android", "fonts")
        fonts = {
            'IBM Plex Sans Medium': os.path.join(font_dir, 'IBMPlexSans-Medium.ttf'),
            'IBM Plex Sans Condensed Bold': os.path.join(font_dir, 'IBMPlexSansCondensed-Bold.ttf'),
            'Roboto': os.path.join(font_dir, 'Roboto-Regular.ttf')
        }
        
        for font_name, font_path in fonts.items():
            if os.path.exists(font_path):
                LabelBase.register(name=font_name, fn_regular=font_path)
            else:
                logger.warning(f"Font file not found: {font_path}")
                
    except Exception as e:
        logger.error(f"Failed to setup fonts: {e}")

    # Load MSI theme colors
    try:
        theme_path = os.path.join("assets", "common", "msi_theme.json")
        with open(theme_path, 'r') as f:
            theme = json.load(f)
            
        # Configure KivyMD theme colors
        app = MDApp.get_running_app()
        app.theme_cls.theme_style = "Dark"
        app.theme_cls.primary_palette = "Green"  # Use MSI green color
        app.theme_cls.accent_palette = "Lime"
        
        # Set custom colors
        app.theme_cls.primary_dark = theme.get("primary_dark", "#1B5E20")
        app.theme_cls.primary_light = theme.get("primary_light", "#A4D233")
        
    except Exception as e:
        logger.error(f"Failed to load theme: {e}")

# Status colors for consistent UI feedback
class StatusColors:
    """Color constants for status messages"""
    ERROR = "#FF3B30"
    SUCCESS = "#34C759"
    NORMAL = "#FFFFFF"
    INACTIVE = "gray60"
    WARNING = "#F39C12"

# Common styles for UI components
class Styles:
    """Common styles for UI components"""
    BUTTON_HEIGHT = dp(48)
    BUTTON_FONT_SIZE = dp(16)
    
    ENTRY_HEIGHT = dp(48)
    ENTRY_FONT_SIZE = dp(16)
    
    TITLE_FONT_SIZE = dp(24)
    SUBTITLE_FONT_SIZE = dp(18)
    BODY_FONT_SIZE = dp(14)
    
    PADDING = dp(16)
    SPACING = dp(8)
    
    # Status bar height on Android
    STATUS_BAR_HEIGHT = dp(24)
    
    # Common styles dictionary for KV language
    KV_STYLES = {
        'standard_button': {
            'height': BUTTON_HEIGHT,
            'font_size': BUTTON_FONT_SIZE,
            'padding': [PADDING, 0],
            'md_bg_color': '#A4D233',  # MSI green
        },
        'entry_field': {
            'height': ENTRY_HEIGHT,
            'font_size': ENTRY_FONT_SIZE,
            'padding': [PADDING, 0],
            'multiline': False,
        },
        'title_label': {
            'font_size': TITLE_FONT_SIZE,
            'bold': True,
            'halign': 'center',
        },
        'status_label': {
            'font_size': SUBTITLE_FONT_SIZE,
            'halign': 'center',
        }
    }