#!/usr/bin/env python3
"""
Simplified Internal Test Script - Tests code logic without external dependencies
"""

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Set test mode
os.environ["TEST_MODE"] = "true"

print("=" * 60)
print("Internal Testing Started")
print("=" * 60)
print()

print("[1/3]Testing Exceptions")
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
    
    exc = PostpartumException("Test", "TEST", {"key": "value"})
    assert exc.message == "Test"
    assert exc.error_code == "TEST"
    assert exc.details == {"key": "value"}
    print("✅ PostpartumException")
    
    exc = AuthenticationError("Auth failed")
    assert exc.error_code == "AUTH_ERROR"
    print("✅ AuthenticationError")
    
    exc = ValidationError("Invalid input")
    assert exc.error_code == "VALIDATION_ERROR"
    print("✅ ValidationError")
    
    exc = AIServiceError("AI unavailable")
    assert exc.error_code == "AI_SERVICE_ERROR"
    print("✅ AIServiceError")
    
    exc = DatabaseError("DB connection failed")
    assert exc.error_code == "DATABASE_ERROR"
    print("✅ DatabaseError")
    
    exc = TaskQueueError("Task failed")
    assert exc.error_code == "TASK_QUEUE_ERROR"
    print("✅ TaskQueueError")
    
    exc = NotFoundError("Not found")
    assert exc.error_code == "NOT_FOUND_ERROR"
    print("✅ NotFoundError")
    
    exc = AuthorizationError("Unauthorized")
    assert exc.error_code == "AUTHORIZATION_ERROR"
    print("✅ AuthorizationError")
    
    exc = ConflictError("Conflict")
    assert exc.error_code == "CONFLICT_ERROR"
    print("✅ ConflictError")
    
    exc = ServiceUnavailableError("Service down")
    assert exc.error_code == "SERVICE_UNAVAILABLE"
    print("✅ ServiceUnavailableError")
    
    exc = RateLimitError("Rate limit exceeded")
    assert exc.error_code == "RATE_LIMIT_ERROR"
    print("✅ RateLimitError")
    
    print("\n✅ All exception class tests passed")
    
except Exception as e:
    print(f"❌ Exception class tests failed: {e}")
    import traceback
    traceback.print_exc()

print("\n[2/3]Testing Error Handlers")
print("-" * 60)

try:
    from middleware.error_handler import (
        postpartum_exception_handler,
        validation_exception_handler,
        http_exception_handler,
        general_exception_handler
    )
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from unittest.mock import Mock
    import asyncio
    
    async def test_handlers():
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.state.user_id = "test_user"
        
        # Testing PostpartumException handler
        exc = NotFoundError("Resource not found")
        response = await postpartum_exception_handler(request, exc)
        assert response.status_code == 404
        print("✅ NotFoundError returns 404")
        
        exc = AuthenticationError("Auth failed")
        response = await postpartum_exception_handler(request, exc)
        assert response.status_code == 401
        print("✅ AuthenticationError returns 401")
        
        exc = AuthorizationError("Unauthorized")
        response = await postpartum_exception_handler(request, exc)
        assert response.status_code == 403
        print("✅ AuthorizationError returns 403")
        
        exc = ConflictError("Conflict")
        response = await postpartum_exception_handler(request, exc)
        assert response.status_code == 409
        print("✅ ConflictError returns 409")
        
        exc = RateLimitError("Rate limit")
        response = await postpartum_exception_handler(request, exc)
        assert response.status_code == 429
        print("✅ RateLimitError returns 429")
        
        exc = ServiceUnavailableError("Service down")
        response = await postpartum_exception_handler(request, exc)
        assert response.status_code == 503
        print("✅ ServiceUnavailableError returns 503")
        
        validation_error = RequestValidationError([{"loc": ["body", "field"], "msg": "required", "type": "value_error"}])
        response = await validation_exception_handler(request, validation_error)
        assert response.status_code == 422
        print("✅ ValidationException returns 422")
        
        # Testing HTTP exception handler
        http_exc = StarletteHTTPException(status_code=404, detail="Not found")
        response = await http_exception_handler(request, http_exc)
        assert response.status_code == 404
        print("✅ HTTPException handler")
        
        general_exc = Exception("General error")
        response = await general_exception_handler(request, general_exc)
        assert response.status_code == 500
        print("✅ GeneralException returns 500")
    
    asyncio.run(test_handlers())
    print("\n✅ All error handler tests passed")
    
except Exception as e:
    print(f"❌ Error handler tests failed: {e}")
    import traceback
    traceback.print_exc()

print("\n[3/3]Testing Configuration")
print("-" * 60)

try:
    from config.settings import get_settings
    settings = get_settings()
    
    assert settings is not None
    print("✅ Settings object exists")
    
    assert hasattr(settings, "test_mode")
    print("✅ Settings has test_mode attribute")
    
    assert hasattr(settings, "database_url")
    print("✅ Settings has database_url attribute")
    
    print("\n✅ All configuration tests passed")
    
except Exception as e:
    print(f"❌ Configuration tests failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Testing Completed")
print("=" * 60)


