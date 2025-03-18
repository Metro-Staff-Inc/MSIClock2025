"""
Settings management for MSI Time Clock.
Provides functionality to load, validate, and access application settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from .platform import Platform

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages application settings and configuration"""

    def __init__(self, settings_path: str = 'settings.json'):
        """Initialize the settings manager
        
        Args:
            settings_path: Path to the settings file
        """
        self.settings_path = settings_path
        self._settings = self._load_settings()
        self._validate_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from the JSON file
        
        Returns:
            dict: The loaded settings
            
        Raises:
            FileNotFoundError: If settings file doesn't exist
            json.JSONDecodeError: If settings file is invalid JSON
        """
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r') as f:
                    settings = json.load(f)
                logger.debug("Successfully loaded settings from %s", self.settings_path)
                return settings
            else:
                logger.warning("Settings file not found at %s, creating default settings", self.settings_path)
                return self._create_default_settings()
        except Exception as e:
            logger.error("Failed to load settings: %s", e)
            raise

    def _create_default_settings(self) -> Dict[str, Any]:
        """Create default settings
        
        Returns:
            dict: The default settings
        """
        from msi_core.auth.password_utils import hash_password

        default_settings = {
            "platform": "linux",  # Default to Linux platform
            "soap": {
                "username": "",
                "password": "",
                "endpoint": "http://msiwebtrax.com/",
                "timeout": 30,
                "clientId": 185
            },
            "camera": {
                "deviceId": 0,
                "captureQuality": 85,
                "resolution": {
                    "width": 640,
                    "height": 480
                },
                "maxWidth": 320,
                "maxHeight": 320
            },
            "ui": {
                "fullscreen": False,
                "language": "en",
                "adminShortcut": "ctrl+alt+a",
                "adminPassword": hash_password("Metro2024!"),
                "firstLaunch": True
            },
            "storage": {
                "retentionDays": 30,
                "dbPath": "data/local.json",
                "maxOfflineRecords": 10000
            },
            "logging": {
                "level": "INFO",
                "maxSize": 10485760,
                "backupCount": 5
            }
        }

        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, 'w') as f:
                json.dump(default_settings, f, indent=2)
            logger.info("Created default settings file at %s", self.settings_path)
            return default_settings
        except Exception as e:
            logger.error("Failed to create default settings: %s", e)
            raise

    def _validate_settings(self):
        """Validate the loaded settings
        
        Raises:
            ValueError: If settings are invalid
        """
        # Validate platform
        try:
            platform_str = self._settings.get('platform', '')
            self._platform = Platform.from_string(platform_str)
        except ValueError as e:
            logger.error("Invalid platform setting: %s", e)
            raise

        # Validate required sections exist
        required_sections = ['soap', 'camera', 'ui', 'storage', 'logging']
        for section in required_sections:
            if section not in self._settings:
                raise ValueError(f"Missing required settings section: {section}")

    @property
    def platform(self) -> Platform:
        """Get the configured platform
        
        Returns:
            Platform: The configured platform enum value
        """
        return self._platform

    def get_settings(self) -> Dict[str, Any]:
        """Get all settings
        
        Returns:
            dict: The complete settings dictionary
        """
        return self._settings

    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """Get a specific settings section
        
        Args:
            section: Name of the settings section
            
        Returns:
            Optional[dict]: The settings section or None if it doesn't exist
        """
        return self._settings.get(section)

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save new settings
        
        Args:
            settings: New settings to save
            
        Returns:
            bool: True if settings were saved successfully
        """
        try:
            # Validate new settings before saving
            self._settings = settings
            self._validate_settings()

            # Save to file
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
            logger.info("Successfully saved settings to %s", self.settings_path)
            return True
        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            self._settings = self._load_settings()  # Reload original settings
            return False

    def update_section(self, section: str, values: Dict[str, Any]) -> bool:
        """Update a specific settings section
        
        Args:
            section: Name of the section to update
            values: New values for the section
            
        Returns:
            bool: True if settings were updated successfully
        """
        try:
            if section not in self._settings:
                self._settings[section] = {}
            self._settings[section].update(values)
            return self.save_settings(self._settings)
        except Exception as e:
            logger.error("Failed to update settings section %s: %s", section, e)
            return False