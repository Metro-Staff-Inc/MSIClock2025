import bcrypt
import logging

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logging.error(f"Failed to hash password: {e}")
        raise

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Check if the password matches the hash
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logging.error(f"Failed to verify password: {e}")
        return False