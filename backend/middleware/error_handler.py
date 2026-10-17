"""
Error Handler Middleware - Unified error handling
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from exceptions import PostpartumException
from services.logging_service import logger


async def postpartum_exception_handler(request: Request, exc: PostpartumException):
    """Handle Postpartum custom exceptions"""
    from exceptions import (
        NotFoundError,
        AuthenticationError,
        AuthorizationError,
        ConflictError,
        RateLimitError,
        ServiceUnavailableError,
        DatabaseError, AIServiceError, TaskQueueError,
    )
    
    logger.log_error(
        error=exc,
        context={
            "route": getattr(request.scope.get("route"), "path", "/"),
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
    elif isinstance(exc, (DatabaseError, AIServiceError, TaskQueueError)):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    internal_error = isinstance(exc, (DatabaseError, AIServiceError, TaskQueueError, ServiceUnavailableError))
    expose_details = not internal_error
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message if expose_details else "Unable to complete the request. Please try again later.",
                "code": exc.error_code,
                "details": exc.details if expose_details else {}
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    # Validation payloads can contain passwords, health text and non-JSON exception objects.
    errors = [
        {"type": item["type"], "loc": item["loc"], "msg": item["msg"]}
        for item in exc.errors()
    ]
    logger.log_error(
        error=ValueError("Request validation failed"),
        context={
            "route": getattr(request.scope.get("route"), "path", "/"),
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
            "route": getattr(request.scope.get("route"), "path", "/"),
            "method": request.method,
            "status_code": exc.status_code
        },
        user_id=getattr(request.state, "user_id", None)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": {
                "type": "HTTPException",
                "message": (
                    "Unable to complete the request. Please try again later."
                    if exc.status_code >= 500 else exc.detail
                ),
                "code": f"HTTP_{exc.status_code}",
                "details": {}
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Return a safe failure; diagnostics never include request text or SQL parameters."""
    from config.settings import get_settings

    logger.log_error(exc, context={
        "route": getattr(request.scope.get("route"), "path", "/"),
        "method": request.method,
        "status_code": 500,
    })
    details = {"error_type": type(exc).__name__} if get_settings().debug else None
    return JSONResponse(status_code=500, content={
        "error": {
            "type": "InternalServerError",
            "message": "An internal server error occurred",
            "code": "INTERNAL_ERROR",
            "recovered": False,
            "details": details,
        }
    })
