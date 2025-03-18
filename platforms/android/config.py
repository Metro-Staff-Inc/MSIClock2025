"""
Android-specific configuration for MSI Time Clock.
Provides Android-specific settings and defaults.
"""

import os
import json
import logging
from typing import Dict, Any
from msi_core.config.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

class AndroidSettingsManager(SettingsManager):
    """Android-specific settings manager"""

    def _create_default_settings(self) -> Dict[str, Any]:
        """Create Android-specific default settings
        
        Returns:
            dict: The default settings with Android-specific values
        """
        from msi_core.auth.password_utils import hash_password

        default_settings = {
            "platform": "android",
            "soap": {
                "username": "MSITIMECLOCK",  # Default Android credentials
                "password": "MarketStaff1",  # Default Android credentials
                "endpoint": "http://msiwebtrax.com/",
                "timeout": 30,
                "clientId": 165
            },
            "camera": {
                "deviceId": 0,
                "captureQuality": 85,
                "resolution": {
                    "width": 1280,  # Higher resolution for Android
                    "height": 720   # Higher resolution for Android
                },
                "maxWidth": 640,
                "maxHeight": 640
            },
            "ui": {
                "fullscreen": True,
                "language": "en",
                "adminShortcut": None,  # Android uses menu button instead
                "adminPassword": hash_password("Metro2024!"),
                "firstLaunch": False,  # Android never shows first launch dialog
                "theme": "dark",
                "fontSize": {
                    "small": 14,
                    "medium": 18,
                    "large": 24,
                    "xlarge": 32
                }
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
            logger.info("Created Android default settings file at %s", self.settings_path)
            return default_settings
        except Exception as e:
            logger.error("Failed to create Android default settings: %s", e)
            raise