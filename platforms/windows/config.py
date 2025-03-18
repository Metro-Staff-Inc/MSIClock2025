"""
Windows-specific configuration for MSI Time Clock.
Provides Windows-specific settings and defaults.
"""

import os
import json
import logging
from typing import Dict, Any
from msi_core.config.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

class WindowsSettingsManager(SettingsManager):
    """Windows-specific settings manager"""

    def _create_default_settings(self) -> Dict[str, Any]:
        """Create Windows-specific default settings
        
        Returns:
            dict: The default settings with Windows-specific values
        """
        from msi_core.auth.password_utils import hash_password

        default_settings = {
            "platform": "windows",
            "soap": {
                "username": "MSITIMECLOCK",  # Default Windows credentials
                "password": "MarketStaff1",         # Default Windows credentials
                "endpoint": "http://msiwebtrax.com/",
                "timeout": 30,
                "clientId": 165
            },
            "ui": {
                "fullscreen": False,
                "language": "en",
                "adminShortcut": "<Control-Alt-a>",
                "adminPassword": hash_password("Metro2024!"),
                "firstLaunch": False  # Windows never shows first launch dialog
            },
            "storage": {
                "retentionDays": 10,
                "dbPath": "data/local.json",
                "maxOfflineRecords": 1000
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
            logger.info("Created Windows default settings file at %s", self.settings_path)
            return default_settings
        except Exception as e:
            logger.error("Failed to create Windows default settings: %s", e)
            raise