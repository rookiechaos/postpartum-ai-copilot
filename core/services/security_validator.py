"""
Security Validator - Input validation and security checks
"""

import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, validator, Field


class PasswordValidator:
    """Password strength validator"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = False  # Optional for better UX
    
    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength
        
        Returns:
            (is_valid, error_message)
        """
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters long"
        
        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must be no more than {cls.MAX_LENGTH} characters long"
        
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if cls.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        # Check for common weak passwords
        weak_passwords = [
            "password", "12345678", "qwerty", "abc123",
            "password123", "admin", "letmein"
        ]
        if password.lower() in weak_passwords:
            return False, "Password is too common. Please choose a stronger password"
        
        return True, None


class InputSanitizer:
    """Input sanitization utilities"""
    
    MAX_STRING_LENGTH = 10000
    MAX_EMAIL_LENGTH = 255
    MAX_USER_ID_LENGTH = 100
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize string input
        
        Args:
            value: Input string
            max_length: Maximum length (default: MAX_STRING_LENGTH)
        
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        max_len = max_length or cls.MAX_STRING_LENGTH
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Truncate if too long
        if len(value) > max_len:
            value = value[:max_len]
        
        # Strip whitespace
        value = value.strip()
        
        return value
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """
        Validate email format
        
        Args:
            email: Email address
        
        Returns:
            True if valid
        """
        if not email or len(email) > cls.MAX_EMAIL_LENGTH:
            return False
        
        # Basic email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @classmethod
    def validate_user_id(cls, user_id: str) -> bool:
        """
        Validate user ID format
        
        Args:
            user_id: User ID
        
        Returns:
            True if valid
        """
        if not user_id or len(user_id) > cls.MAX_USER_ID_LENGTH:
            return False
        
        # Allow alphanumeric, underscore, and hyphen
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, user_id))
    
    @classmethod
    def sanitize_sql_like(cls, value: str) -> str:
        """
        Sanitize string for SQL LIKE queries
        
        Args:
            value: Input string
        
        Returns:
            Sanitized string with escaped special characters
        """
        # Escape SQL LIKE special characters
        value = value.replace('\\', '\\\\')
        value = value.replace('%', '\\%')
        value = value.replace('_', '\\_')
        return value


class RateLimitChecker:
    """Rate limiting utilities"""
    
    @staticmethod
    def check_rate_limit(
        identifier: str,
        limit: int,
        window: int,
        current_count: int
    ) -> tuple[bool, Optional[str]]:
        """
        Check if rate limit is exceeded
        
        Args:
            identifier: User identifier (IP, user_id, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
            current_count: Current request count
        
        Returns:
            (is_allowed, error_message)
        """
        if current_count >= limit:
            return False, f"Rate limit exceeded. Maximum {limit} requests per {window} seconds"
        
        return True, None


class SecurityHeaders:
    """Security headers configuration"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """
        Get recommended security headers
        
        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }


class CSRFProtection:
    """CSRF protection utilities"""
    
    @staticmethod
    def generate_csrf_token() -> str:
        """
        Generate CSRF token
        
        Returns:
            CSRF token string
        """
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_csrf_token(token: str, stored_token: str) -> bool:
        """
        Verify CSRF token
        
        Args:
            token: Token from request
            stored_token: Token stored in session
        
        Returns:
            True if valid
        """
        import secrets
        if not token or not stored_token:
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(token, stored_token)

