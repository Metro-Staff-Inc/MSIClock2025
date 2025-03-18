#!/usr/bin/env python3
"""
MSI Time Clock - Main Entry Point
This is the universal entry point for the MSI Time Clock application.
It determines which platform-specific implementation to use based on configuration.
"""

import os
import sys
import logging
from typing import Optional
from msi_core.config.platform import Platform
from msi_core.config.settings_manager import SettingsManager

def setup_logging():
    """Set up logging configuration"""
    log_dir = "logs"
    try:
        # Create logs directory with proper permissions
        os.makedirs(log_dir, mode=0o777, exist_ok=True)
        
        # Try to load settings to get log level
        log_level = logging.INFO  # Default to INFO
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                level_str = settings.get('logging', {}).get('level', 'INFO')
                log_level = getattr(logging, level_str)
                print(f"Setting log level to: {level_str}")
        except Exception as e:
            print(f"Could not load log level from settings: {e}")
        
        # Create custom formatter that handles both normal and separator formats
        class CustomFormatter(logging.Formatter):
            def format(self, record):
                # Special handling for separator messages
                if record.msg.startswith('='*50) or record.msg.startswith('APPLICATION START'):
                    return record.getMessage()
                
                # Normal message handling
                original_levelname = record.levelname
                # Only show level if not INFO
                if record.levelno == logging.INFO:
                    record.levelname = ""
                # Format with timestamp
                result = f"{self.formatTime(record)} - {record.levelname} - {record.getMessage()}"
                # Restore original levelname
                record.levelname = original_levelname
                # Clean up extra dash for INFO level
                if record.levelno == logging.INFO:
                    result = result.replace(" -  -", " -")
                return result

        # Configure logging with custom formatter
        formatter = CustomFormatter('%(asctime)s - %(levelname)s - %(message)s')
        handlers = [
            logging.FileHandler(os.path.join(log_dir, 'app.log')),
            logging.StreamHandler(sys.stdout)
        ]
        for handler in handlers:
            handler.setFormatter(formatter)
        
        logging.basicConfig(
            level=log_level,
            handlers=handlers
        )
        
        # Set all loggers to the configured level
        for logger_name in logging.root.manager.loggerDict:
            logging.getLogger(logger_name).setLevel(log_level)
            
        # Log the level that was set
        logging.debug(f"Logging initialized with level: {logging.getLevelName(log_level)}")
        
    except Exception as e:
        # If we can't write to logs, fall back to console only
        print(f"Warning: Could not set up file logging: {e}")
        # Use same custom formatter for fallback logging
        fallback_handler = logging.StreamHandler(sys.stdout)
        fallback_handler.setFormatter(CustomFormatter())
        logging.basicConfig(
            level=logging.DEBUG,  # Use DEBUG for fallback to capture everything
            handlers=[fallback_handler]
        )

def get_platform_implementation(platform: Platform) -> Optional[str]:
    """Get the appropriate platform implementation module
    
    Args:
        platform: The platform to get the implementation for
        
    Returns:
        Optional[str]: The module path for the platform implementation, or None if not found
    """
    implementations = {
        Platform.LINUX: "platforms.linux.main",
        Platform.ANDROID: "platforms.android.main",
        Platform.WINDOWS: "platforms.windows.main"
    }
    return implementations.get(platform)

def main():
    """Main entry point for the application"""
    # Set up logging first
    setup_logging()
    
    try:
        # Add application start separator
        logging.info("="*50)
        logging.info(f"APPLICATION START - {datetime.now().strftime('%A, %B %d, %Y %I:%M:%S %p')}")
        logging.info("="*50)
        
        # Load settings and get configured platform
        settings_manager = SettingsManager()
        platform = settings_manager.platform
        
        # Get the appropriate implementation
        implementation_module = get_platform_implementation(platform)
        if not implementation_module:
            logging.error(f"No implementation found for platform: {platform.value}")
            sys.exit(1)
            
        # Import and run the platform-specific implementation
        try:
            module = __import__(implementation_module, fromlist=['main'])
            platform_main = getattr(module, 'main')
            platform_main()
        except ImportError as e:
            logging.error(f"Failed to import {platform.value} implementation: {e}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error in {platform.value} implementation: {e}")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
