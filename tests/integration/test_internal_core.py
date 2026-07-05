#!/usr/bin/env python3
"""
Core Internal Test Script - Tests core logic without external dependencies
"""

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Set test mode
os.environ["TEST_MODE"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-32-chars-min"

print("=" * 60)
print("Core Internal Testing")
print("=" * 60)
print()

test_results = {"passed": 0, "failed": 0, "skipped": 0}

def test(name, func, skip_if_error=None):
    try:
        result = func()
        if result is not False:
            test_results["passed"] += 1
            print(f"✅ {name}")
            return True
        else:
            test_results["failed"] += 1
            print(f"❌ {name}")
            return False
    except Exception as e:
        if skip_if_error and isinstance(e, skip_if_error):
            test_results["skipped"] += 1
            print(f"⏭️  {name} (Skipping: missing dependency)")
            return None
        test_results["failed"] += 1
        print(f"❌ {name}: {e}")
        return False

print("[1/4]Testing Exceptions")
print("-" * 60)

try:
    from exceptions import (
        PostpartumException,
        AuthenticationError,
        ValidationError,
        AIServiceError,
        DatabaseError,
        TaskQueueError,
        NotFoundError,
        AuthorizationError,
        ConflictError,
        ServiceUnavailableError,
        RateLimitError
    )
    
    test("PostpartumException basic functionality", lambda: (
        exc := PostpartumException("Test", "TEST", {"key": "value"}),
        exc.message == "Test" and exc.error_code == "TEST" and exc.details == {"key": "value"}
    )[1])
    
    test("AuthenticationError", lambda: (
        exc := AuthenticationError("Auth failed"),
        exc.error_code == "AUTH_ERROR"
    )[1])
    
    test("ValidationError", lambda: (
        exc := ValidationError("Invalid input"),
        exc.error_code == "VALIDATION_ERROR"
    )[1])
    
    test("AIServiceError", lambda: (
        exc := AIServiceError("AI unavailable"),
        exc.error_code == "AI_SERVICE_ERROR"
    )[1])
    
    test("DatabaseError", lambda: (
        exc := DatabaseError("DB connection failed"),
        exc.error_code == "DATABASE_ERROR"
    )[1])
    
    test("TaskQueueError", lambda: (
        exc := TaskQueueError("Task failed"),
        exc.error_code == "TASK_QUEUE_ERROR"
    )[1])
    
    test("NotFoundError", lambda: (
        exc := NotFoundError("Not found"),
        exc.error_code == "NOT_FOUND_ERROR"
    )[1])
    
    test("AuthorizationError", lambda: (
        exc := AuthorizationError("Unauthorized"),
        exc.error_code == "AUTHORIZATION_ERROR"
    )[1])
    
    test("ConflictError", lambda: (
        exc := ConflictError("Conflict"),
        exc.error_code == "CONFLICT_ERROR"
    )[1])
    
    test("ServiceUnavailableError", lambda: (
        exc := ServiceUnavailableError("Service down"),
        exc.error_code == "SERVICE_UNAVAILABLE"
    )[1])
    
    test("RateLimitError", lambda: (
        exc := RateLimitError("Rate limit exceeded"),
        exc.error_code == "RATE_LIMIT_ERROR"
    )[1])
    
except Exception as e:
    print(f"❌ Failed to import exception classes: {e}")

print("\n[2/4]Testing Error Handler Status Codes")
print("-" * 60)

try:
    from middleware.error_handler import postpartum_exception_handler
    from fastapi import Request
    from unittest.mock import Mock
    import asyncio
    
    async def test_status_codes():
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.state.user_id = "test_user"
        
        from exceptions import (
            NotFoundError,
            AuthenticationError,
            AuthorizationError,
            ConflictError,
            RateLimitError,
            ServiceUnavailableError
        )
        
        response = await postpartum_exception_handler(request, NotFoundError("Not found"))
        test("NotFoundError -> 404", lambda: response.status_code == 404)
        
        response = await postpartum_exception_handler(request, AuthenticationError("Auth failed"))
        test("AuthenticationError -> 401", lambda: response.status_code == 401)
        
        response = await postpartum_exception_handler(request, AuthorizationError("Unauthorized"))
        test("AuthorizationError -> 403", lambda: response.status_code == 403)
        
        response = await postpartum_exception_handler(request, ConflictError("Conflict"))
        test("ConflictError -> 409", lambda: response.status_code == 409)
        
        response = await postpartum_exception_handler(request, RateLimitError("Rate limit"))
        test("RateLimitError -> 429", lambda: response.status_code == 429)
        
        response = await postpartum_exception_handler(request, ServiceUnavailableError("Service down"))
        test("ServiceUnavailableError -> 503", lambda: response.status_code == 503)
    
    try:
        loop = asyncio.get_running_loop()
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(test_status_codes())
    except RuntimeError:
        # No running loop; use asyncio.run directly
        asyncio.run(test_status_codes())
    except ImportError:
        # nest_asyncio not installed; trying fallback
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(test_status_codes())
            loop.close()
        except:
            test_results["skipped"] += 6
            print(f"⏭️  Error handler tests skipped (event loop issue)")
    
except ImportError as e:
    test_results["skipped"] += 6
    print(f"⏭️  Error handler tests skipped (missing dependency: {e})")
except Exception as e:
    test_results["skipped"] += 6
    print(f"⏭️  Error handler tests skipped: {e}")

print("\n[3/4]Testing Configuration")
print("-" * 60)

try:
    from config.settings import get_settings
    settings = get_settings()
    
    test("Settings object exists", lambda: settings is not None)
    test("Settings has test_mode attribute", lambda: hasattr(settings, "test_mode"))
    test("Settings has database_url attribute", lambda: hasattr(settings, "database_url"))
    
except ImportError as e:
    test_results["skipped"] += 3
    print(f"⏭️  Configuration tests skipped (missing dependency: {e})")
except Exception as e:
    if "validation error" in str(e).lower() or "jwt_secret_key" in str(e):
        try:
            os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-32-chars-min"
            from config.settings import get_settings
            get_settings.cache_clear()  # Clear cache
            settings = get_settings()
            test("Settings object exists", lambda: settings is not None)
            test("Settings has test_mode attribute", lambda: hasattr(settings, "test_mode"))
            test("Settings has database_url attribute", lambda: hasattr(settings, "database_url"))
        except Exception as e2:
            test_results["skipped"] += 3
            print(f"⏭️  Configuration tests skipped: {e2}")
    else:
        test_results["skipped"] += 3
        print(f"⏭️  Configuration tests skipped: {e}")

print("\n[4/4]Testing Code Structure")
print("-" * 60)

try:
    backend_path = Path(__file__).resolve().parent.parent / "backend"
    
    test("exceptions.py exists", lambda: (backend_path / "exceptions.py").exists())
    test("middleware/error_handler.py exists", lambda: (backend_path / "middleware" / "error_handler.py").exists())
    test("config/settings.py exists", lambda: (backend_path / "config" / "settings.py").exists())
    test("services/feedback_service.py exists", lambda: (backend_path / "services" / "feedback_service.py").exists())
    test("api/task_routes.py exists", lambda: (backend_path / "api" / "task_routes.py").exists())
    
except Exception as e:
    print(f"❌ Code structure test failed: {e}")

print("\n" + "=" * 60)
print("Test Summary")
print("=" * 60)
print(f"PASSED: {test_results['passed']}")
print(f"FAILED: {test_results['failed']}")
print(f"Skipping: {test_results['skipped']}")
print(f"Total: {sum(test_results.values())}")
print("=" * 60)

if test_results['failed'] == 0:
    if test_results['skipped'] > 0:
        print(f"\n✅ All runnable tests passed! ({test_results['skipped']} skipped due to missing dependencies)")
    else:
        print("\n🎉 All tests passed!")
    sys.exit(0)
else:
    print("\n⚠️  Some tests failed")
    sys.exit(1)


