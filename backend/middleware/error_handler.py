"""
Error Handler Middleware - Unified error handling
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from exceptions import PostpartumException
from services.logging_service import logger
import traceback


async def postpartum_exception_handler(request: Request, exc: PostpartumException):
    """Handle Postpartum custom exceptions"""
    from exceptions import (
        NotFoundError,
        AuthenticationError,
        AuthorizationError,
        ConflictError,
        RateLimitError,
        ServiceUnavailableError
    )
    
    logger.log_error(
        error=exc,
        context={
            "endpoint": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "details": exc.details
        },
        user_id=getattr(request.state, "user_id", None)
    )
    
    # Map exception types to appropriate HTTP status codes
    status_code = status.HTTP_400_BAD_REQUEST  # Default
    if isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, AuthenticationError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, AuthorizationError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, RateLimitError):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(exc, ServiceUnavailableError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message,
                "code": exc.error_code,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = exc.errors()
    logger.log_error(
        error=exc,
        context={
            "endpoint": request.url.path,
            "method": request.method,
            "validation_errors": errors
        },
        user_id=getattr(request.state, "user_id", None)
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "code": "VALIDATION_ERROR",
                "details": {
                    "errors": errors
                }
            }
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.log_error(
        error=exc,
        context={
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        },
        user_id=getattr(request.state, "user_id", None)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "code": f"HTTP_{exc.status_code}",
                "details": {}
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle general exceptions
    
    Logs the error and returns a generic error response.
    Attempts to recover from certain errors.
    Ensures no sensitive information is leaked in production.
    """
    from config.settings import get_settings
    
    settings = get_settings()
    
    # Attempt error recovery for certain errors
    error_recovered = False
    recovery_message = None
    
    # Database connection errors - could be transient
    if "database" in str(exc).lower() or "connection" in str(exc).lower():
        recovery_message = "Database connection issue detected. Please retry."
    
    # Network errors - could be transient
    if "timeout" in str(exc).lower() or "network" in str(exc).lower():
        recovery_message = "Network issue detected. Please retry."
        error_recovered = True
    
    # Sanitize error message for production
    error_message = str(exc)
    if not settings.debug:
        # Remove sensitive information from error messages
        sensitive_patterns = [
            r'/[\w/]+\.db',  # Database file paths
            r'/[\w/]+\.log',  # Log file paths
            r'password[=:]\s*\S+',  # Password in error messages
            r'secret[=:]\s*\S+',  # Secret keys
            r'api[_-]?key[=:]\s*\S+',  # API keys
            r'token[=:]\s*\S+',  # Tokens
        ]
        import re
        for pattern in sensitive_patterns:
            error_message = re.sub(pattern, '[REDACTED]', error_message, flags=re.IGNORECASE)
    
    logger.log_error(
        error=exc,
        context={
            "endpoint": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
            "recovered": error_recovered,
            "recovery_message": recovery_message
        },
        user_id=getattr(request.state, "user_id", None)
    )
    
    # Prepare error details - sanitize for production
    error_details = {}
    if settings.debug:
        error_details["traceback"] = traceback.format_exc()
        error_details["error_type"] = type(exc).__name__
        error_details["error_message"] = error_message
    else:
        # In production, only include safe information
        error_details = None
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "InternalServerError",
                "message": recovery_message or "An internal server error occurred",
                "code": "INTERNAL_ERROR",
                "recovered": error_recovered,
                "details": error_details
            }
        }
    )

