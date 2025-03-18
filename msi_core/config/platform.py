"""
Platform configuration for MSI Time Clock.
Defines the supported platforms for the application.
"""

from enum import Enum

class Platform(Enum):
    """Supported platforms for the MSI Time Clock application"""
    LINUX = "linux"
    ANDROID = "android"
    WINDOWS = "windows"

    @classmethod
    def from_string(cls, value: str) -> 'Platform':
        """Convert a string to a Platform enum value
        
        Args:
            value: The string value to convert
            
        Returns:
            Platform: The corresponding Platform enum value
            
        Raises:
            ValueError: If the string is not a valid platform
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_platforms = ", ".join(p.value for p in cls)
            raise ValueError(
                f"Invalid platform '{value}'. "
                f"Must be one of: {valid_platforms}"
            )