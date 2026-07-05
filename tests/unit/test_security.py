"""
Security tests - Test security features and validations
"""

import pytest
from services.security_validator import (
    PasswordValidator,
    InputSanitizer,
    SecurityHeaders,
    CSRFProtection
)
from exceptions import ValidationError


def test_password_validation_weak():
    """Test password validation with weak passwords"""
    # Too short
    is_valid, error = PasswordValidator.validate_password("short")
    assert is_valid is False
    assert "at least" in error.lower()
    
    # No uppercase
    is_valid, error = PasswordValidator.validate_password("lowercase123")
    assert is_valid is False
    assert "uppercase" in error.lower()
    
    # No lowercase
    is_valid, error = PasswordValidator.validate_password("UPPERCASE123")
    assert is_valid is False
    assert "lowercase" in error.lower()
    
    # No digit
    is_valid, error = PasswordValidator.validate_password("NoDigits")
    assert is_valid is False
    assert "digit" in error.lower()
    
    # Common password
    is_valid, error = PasswordValidator.validate_password("password123")
    assert is_valid is False
    assert "common" in error.lower() or "too common" in error.lower()


def test_password_validation_strong():
    """Test password validation with strong passwords"""
    is_valid, error = PasswordValidator.validate_password("StrongPass123")
    assert is_valid is True
    assert error is None


def test_password_validation_too_long():
    """Test password validation with too long password"""
    long_password = "A" * 200
    is_valid, error = PasswordValidator.validate_password(long_password)
    assert is_valid is False
    assert "no more than" in error.lower()


def test_email_validation():
    """Test email validation"""
    # Valid emails
    assert InputSanitizer.validate_email("test@example.com") is True
    assert InputSanitizer.validate_email("user.name@domain.co.uk") is True
    
    # Invalid emails
    assert InputSanitizer.validate_email("invalid") is False
    assert InputSanitizer.validate_email("invalid@") is False
    assert InputSanitizer.validate_email("@domain.com") is False
    assert InputSanitizer.validate_email("") is False


def test_user_id_validation():
    """Test user ID validation"""
    # Valid user IDs
    assert InputSanitizer.validate_user_id("user_123") is True
    assert InputSanitizer.validate_user_id("user-123") is True
    assert InputSanitizer.validate_user_id("user123") is True
    
    # Invalid user IDs
    assert InputSanitizer.validate_user_id("user@123") is False  # Special char
    assert InputSanitizer.validate_user_id("user 123") is False  # Space
    assert InputSanitizer.validate_user_id("") is False


def test_string_sanitization():
    """Test string sanitization"""
    # Remove null bytes
    sanitized = InputSanitizer.sanitize_string("test\x00string")
    assert "\x00" not in sanitized
    
    # Truncate long strings
    long_string = "A" * 20000
    sanitized = InputSanitizer.sanitize_string(long_string, max_length=100)
    assert len(sanitized) == 100
    
    # Strip whitespace
    sanitized = InputSanitizer.sanitize_string("  test  ")
    assert sanitized == "test"


def test_sql_like_sanitization():
    """Test SQL LIKE sanitization"""
    # Escape special characters
    sanitized = InputSanitizer.sanitize_sql_like("test%_value")
    assert "%" not in sanitized or sanitized.count("%") == sanitized.count("\\%")
    assert "_" not in sanitized or sanitized.count("_") == sanitized.count("\\_")


def test_security_headers():
    """Test security headers generation"""
    headers = SecurityHeaders.get_security_headers()
    
    assert "X-Content-Type-Options" in headers
    assert "X-Frame-Options" in headers
    assert "X-XSS-Protection" in headers
    assert "Strict-Transport-Security" in headers
    assert "Content-Security-Policy" in headers
    assert headers["X-Frame-Options"] == "DENY"


def test_csrf_token_generation():
    """Test CSRF token generation"""
    token1 = CSRFProtection.generate_csrf_token()
    token2 = CSRFProtection.generate_csrf_token()
    
    assert token1 != token2
    assert len(token1) > 0
    assert isinstance(token1, str)


def test_csrf_token_verification():
    """Test CSRF token verification"""
    token = CSRFProtection.generate_csrf_token()
    
    # Valid token
    assert CSRFProtection.verify_csrf_token(token, token) is True
    
    # Invalid token
    assert CSRFProtection.verify_csrf_token(token, "different_token") is False
    
    # Empty tokens
    assert CSRFProtection.verify_csrf_token("", "") is False
    assert CSRFProtection.verify_csrf_token(token, "") is False


def test_rate_limit_checker():
    """Test rate limit checking"""
    from services.security_validator import RateLimitChecker
    
    # Within limit
    is_allowed, error = RateLimitChecker.check_rate_limit("user1", 10, 60, 5)
    assert is_allowed is True
    assert error is None
    
    # Exceeded limit
    is_allowed, error = RateLimitChecker.check_rate_limit("user1", 10, 60, 10)
    assert is_allowed is False
    assert "exceeded" in error.lower()


@pytest.mark.asyncio
async def test_password_strength_in_user_creation(test_db_session):
    """Test password strength validation in user creation"""
    from services.auth_service import AuthService
    from models.schemas import UserCreate
    
    auth_service = AuthService()
    
    # Weak password should fail
    weak_user = UserCreate(email="weak@example.com", password="weak")
    with pytest.raises(ValidationError):
        auth_service.create_user(weak_user, test_db_session)
    
    # Strong password should succeed
    strong_user = UserCreate(email="strong@example.com", password="StrongPass123")
    user = auth_service.create_user(strong_user, test_db_session)
    assert user.email == "strong@example.com"


@pytest.mark.asyncio
async def test_email_validation_in_user_creation(test_db_session):
    """Test email validation in user creation"""
    from services.auth_service import AuthService
    from models.schemas import UserCreate
    
    auth_service = AuthService()
    
    # Invalid email should fail
    invalid_user = UserCreate(email="invalid-email", password="ValidPass123")
    with pytest.raises(ValidationError):
        auth_service.create_user(invalid_user, test_db_session)
    
    # Valid email should succeed
    valid_user = UserCreate(email="valid@example.com", password="ValidPass123")
    user = auth_service.create_user(valid_user, test_db_session)
    assert user.email == "valid@example.com"
