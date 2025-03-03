"""
Mapping of punch exception codes to user-friendly messages.
This module provides a centralized way to handle punch exceptions
and display appropriate messages to users.
"""

class PunchExceptions:
    """Mapping of punch exception codes to user-friendly messages"""

    # Map exception codes to (English message, Spanish message, status color)
    EXCEPTIONS = {
        # Correct Mappings
        "default": ("Not Authorized. No punch recorded.", "No Authorizado. No registro realizado.", "ERROR"),
        "1": ("Shift not yet started. No punch recorded.", "Turno no ha iniciado. No registro realizado.", "WARNING"),
        "2": ("Not Authorized. No punch recorded.", "No Authorizado. No registro realizado.", "ERROR"),
        "3": ("Shift has finished. No punch recorded.", "Turno ha finalizado. No registro realizado.", "WARNING")
    }
    
    @staticmethod
    def get_message(exception_code):
        """
        Get the appropriate message for an exception code
        
        Args:
            exception_code: The exception code from the SOAP response
            
        Returns:
            Tuple of (English message, Spanish message, status color) or None if no exception
        """
        if not exception_code:
            return None
            
        # Convert to string if it's not already
        exception_code = str(exception_code)
        
        if exception_code in PunchExceptions.EXCEPTIONS:
            return PunchExceptions.EXCEPTIONS[exception_code]
        else:
            # Default message if exception code is not recognized
            return PunchExceptions.EXCEPTIONS["default"]