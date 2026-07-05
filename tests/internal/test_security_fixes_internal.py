"""
Internal Security Fixes Test
"""

import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment variables
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_internal_testing_only_min_32_chars")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_security_fixes.db")
os.environ.setdefault("DEBUG", "True")  # Test in debug mode first
os.environ.setdefault("TEST_MODE", "True")

from config.settings import Settings, get_settings
from exceptions import ValidationError
import warnings


def test_jwt_secret_validation():
    """Test JWT secret key validation"""
    print("\n" + "="*60)
    print("Testing JWT Secret Key Validation")
    print("="*60)
    
    # Test 1: Default value in debug mode (should warn but allow)
    print("\n1. Testing default value in debug mode...")
    os.environ["DEBUG"] = "True"
    os.environ["JWT_SECRET_KEY"] = "change-me-in-production-please-use-strong-random-key"
    
    # Clear cache to force re-initialization
    get_settings.cache_clear()
    
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            settings = get_settings()
            assert len(w) > 0, "Should have warning for default secret"
            assert "insecure" in str(w[0].message).lower()
            print("✅ Default value in debug mode: Warning issued (expected)")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 2: Default value in production (should fail)
    print("\n2. Testing default value in production mode...")
    os.environ["DEBUG"] = "False"
    os.environ["TEST_MODE"] = "False"
    os.environ["JWT_SECRET_KEY"] = "change-me-in-production-please-use-strong-random-key"
    
    get_settings.cache_clear()
    
    try:
        settings = get_settings()
        print("❌ Should have raised ValueError in production")
        return False
    except ValueError as e:
        assert "default value" in str(e).lower() or "production" in str(e).lower()
        print("✅ Default value in production: Correctly rejected")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test 3: Valid secret in production
    print("\n3. Testing valid secret in production mode...")
    os.environ["JWT_SECRET_KEY"] = "a" * 32  # 32 character secret
    
    get_settings.cache_clear()
    
    try:
        settings = get_settings()
        assert settings.jwt_secret_key == "a" * 32
        print("✅ Valid secret in production: Accepted")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Reset for other tests
    os.environ["DEBUG"] = "True"
    os.environ["TEST_MODE"] = "True"
    get_settings.cache_clear()
    
    return True


def test_cors_validation():
    """Test CORS origins validation"""
    print("\n" + "="*60)
    print("Testing CORS Origins Validation")
    print("="*60)
    
    # Test 1: Wildcard in production (should fail)
    print("\n1. Testing wildcard in production mode...")
    os.environ["DEBUG"] = "False"
    os.environ["TEST_MODE"] = "False"
    os.environ["CORS_ORIGINS"] = "*"
    
    get_settings.cache_clear()
    
    try:
        settings = get_settings()
        origins = settings.get_cors_origins_list()
        print("❌ Should have raised ValueError for wildcard in production")
        return False
    except ValueError as e:
        assert "wildcard" in str(e).lower() or "not allowed" in str(e).lower()
        print("✅ Wildcard in production: Correctly rejected")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test 2: Valid origins in production
    print("\n2. Testing valid origins in production mode...")
    os.environ["CORS_ORIGINS"] = "https://example.com,https://app.example.com"
    
    get_settings.cache_clear()
    
    try:
        settings = get_settings()
        origins = settings.get_cors_origins_list()
        assert len(origins) == 2
        assert "https://example.com" in origins
        print("✅ Valid origins in production: Accepted")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 3: Invalid format
    print("\n3. Testing invalid origin format...")
    os.environ["CORS_ORIGINS"] = "invalid-origin"
    
    get_settings.cache_clear()
    
    try:
        settings = Settings()
        print("❌ Should have raised ValueError for invalid format")
        return False
    except ValueError as e:
        assert "format" in str(e).lower() or "http" in str(e).lower()
        print("✅ Invalid format: Correctly rejected")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Reset
    os.environ["DEBUG"] = "True"
    os.environ["TEST_MODE"] = "True"
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"
    get_settings.cache_clear()
    
    return True


def test_file_upload_size_limit():
    """Test file upload size limit configuration"""
    print("\n" + "="*60)
    print("Testing File Upload Size Limit")
    print("="*60)
    
    # Test 1: Default size limit
    print("\n1. Testing default upload size limit...")
    os.environ["DEBUG"] = "True"
    
    get_settings.cache_clear()
    
    try:
        settings = get_settings()
        assert settings.max_upload_size_mb == 10
        max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
        assert max_size_bytes == 10 * 1024 * 1024
        print(f"✅ Default upload size: {settings.max_upload_size_mb}MB")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 2: Custom size limit
    print("\n2. Testing custom upload size limit...")
    os.environ["MAX_UPLOAD_SIZE_MB"] = "20"
    
    get_settings.cache_clear()
    
    try:
        settings = get_settings()
        assert settings.max_upload_size_mb == 20
        print(f"✅ Custom upload size: {settings.max_upload_size_mb}MB")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Reset
    if "MAX_UPLOAD_SIZE_MB" in os.environ:
        del os.environ["MAX_UPLOAD_SIZE_MB"]
    get_settings.cache_clear()
    
    return True


def test_webhook_verification():
    """Test webhook verification in production"""
    print("\n" + "="*60)
    print("Testing Webhook Verification")
    print("="*60)
    
    from utils.webhook_verification import verify_stripe_webhook, verify_paypal_webhook
    from fastapi import HTTPException
    
    # Test 1: Missing secret in production (should fail)
    print("\n1. Testing missing Stripe secret in production...")
    os.environ["DEBUG"] = "False"
    os.environ["TEST_MODE"] = "False"
    if "STRIPE_WEBHOOK_SECRET" in os.environ:
        del os.environ["STRIPE_WEBHOOK_SECRET"]
    
    get_settings.cache_clear()
    
    try:
        verify_stripe_webhook(
            payload=b'{"test": "data"}',
            signature="test_signature"
        )
        print("❌ Should have raised HTTPException in production")
        return False
    except HTTPException as e:
        assert e.status_code == 500
        assert "not configured" in str(e.detail).lower()
        print("✅ Missing secret in production: Correctly rejected")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test 2: Missing secret in debug mode (should allow)
    print("\n2. Testing missing secret in debug mode...")
    os.environ["DEBUG"] = "True"
    os.environ["TEST_MODE"] = "True"
    
    get_settings.cache_clear()
    
    try:
        result = verify_stripe_webhook(
            payload=b'{"test": "data"}',
            signature="test_signature"
        )
        assert result is True
        print("✅ Missing secret in debug mode: Allowed (expected)")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Reset
    os.environ["DEBUG"] = "True"
    os.environ["TEST_MODE"] = "True"
    get_settings.cache_clear()
    
    return True


def test_error_handling_sanitization():
    """Test error handling sanitization"""
    print("\n" + "="*60)
    print("Testing Error Handling Sanitization")
    print("="*60)
    
    # Test that error handler exists and has sanitization logic
    print("\n1. Testing error handler sanitization logic...")
    
    try:
        from middleware.error_handler import general_exception_handler
        import inspect
        
        # Check if function exists and has sanitization logic
        source = inspect.getsource(general_exception_handler)
        assert "sensitive" in source.lower() or "redacted" in source.lower()
        assert "settings.debug" in source
        print("✅ Error handler has sanitization logic")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    return True


def test_password_validation():
    """Test password validation is applied"""
    print("\n" + "="*60)
    print("Testing Password Validation")
    print("="*60)
    
    # Test 1: Check PasswordValidator exists
    print("\n1. Testing PasswordValidator...")
    
    try:
        from services.security_validator import PasswordValidator
        
        # Test weak password
        is_valid, error = PasswordValidator.validate_password("weak")
        assert is_valid is False
        assert error is not None
        print("✅ Weak password rejected")
        
        # Test strong password
        is_valid, error = PasswordValidator.validate_password("StrongPass123")
        assert is_valid is True
        assert error is None
        print("✅ Strong password accepted")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 2: Check UserCreate schema uses validator
    print("\n2. Testing UserCreate schema validation...")
    
    try:
        from models.schemas import UserCreate
        import inspect
        
        source = inspect.getsource(UserCreate)
        assert "validate_password" in source or "PasswordValidator" in source
        print("✅ UserCreate schema uses password validation")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    return True


def run_all_tests():
    """Run all security fix tests"""
    print("\n" + "="*60)
    print("SECURITY FIXES INTERNAL TEST SUITE")
    print("="*60)
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    tests = [
        ("JWT Secret Validation", test_jwt_secret_validation),
        ("CORS Validation", test_cors_validation),
        ("File Upload Size Limit", test_file_upload_size_limit),
        ("Webhook Verification", test_webhook_verification),
        ("Error Handling Sanitization", test_error_handling_sanitization),
        ("Password Validation", test_password_validation),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
                test_results["errors"].append(f"{test_name}: Test returned False")
        except Exception as e:
            test_results["failed"] += 1
            test_results["errors"].append(f"{test_name}: {str(e)}")
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    
    if test_results["errors"]:
        print("\nErrors:")
        for error in test_results["errors"]:
            print(f"  - {error}")
    
    print("="*60)
    
    if test_results["failed"] == 0:
        print("✅ ALL SECURITY FIX TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

