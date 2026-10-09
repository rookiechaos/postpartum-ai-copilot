"""
Rate Limiting Middleware - Prevent API abuse
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from typing import Callable
from functools import wraps
import time
from config.settings import get_settings

# Check if Redis is available for distributed rate limiting
settings = get_settings()
REDIS_URL = settings.redis_url
USE_REDIS = REDIS_URL is not None

if USE_REDIS:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL)
        # Use Redis for distributed rate limiting
        limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL)
    except ImportError:
        # Fallback to memory if redis not available
        limiter = Limiter(key_func=get_remote_address)
        USE_REDIS = False
else:
    # Initialize limiter with in-memory storage
    limiter = Limiter(key_func=get_remote_address)


def get_user_id(request: Request) -> str:
    """Get user ID from request for rate limiting"""
    # Try to get user_id from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    
    # Fallback to IP address
    return get_remote_address(request)


# Rate limit configurations
RATE_LIMITS = {
    "default": "100/minute",
    "chat": "20/minute",  # Chat requests (AI-intensive)
    "auth": "5/minute",  # Very restrictive for auth endpoints
    "task": "30/minute",  # Task creation
    "tracking": "60/minute",  # Tracking entries (more frequent)
}


def rate_limit(limit: str = "100/minute", key_func: Callable = get_remote_address):
    """
    Decorator for rate limiting endpoints with rate limit headers
    
    Usage:
        @app.post("/api/chat")
        @rate_limit(limit="20/minute")
        async def chat(request: Request, ...):
            ...
    """
    # Check if we're in test mode BEFORE creating the decorator
    from config.settings import get_settings
    settings = get_settings()
    test_mode = settings.test_mode
    
    if test_mode:
        # In test mode, return a pass-through decorator that does nothing
        def pass_through_decorator(func):
            return func
        return pass_through_decorator
    
    # In production, create the actual rate limiting decorator
    def decorator(func):
        import inspect
        
        # Check if function has 'request' parameter (required by slowapi)
        sig = inspect.signature(func)
        has_request = 'request' in sig.parameters or 'http_request' in sig.parameters
        
        if not has_request:
            # Function doesn't have request parameter, can't use slowapi
            # Return function as-is (for endpoints that don't need rate limiting)
            return func
        
        # Apply slowapi rate limiting
        try:
            wrapped = limiter.limit(limit, key_func=key_func)(func)
        except Exception as e:
            # If rate limiting fails, log and return function as-is
            # This allows graceful degradation
            import warnings
            warnings.warn(f"Rate limiting failed for {func.__name__}: {e}")
            return func
        
        # Add rate limit headers to response
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                response = await wrapped(*args, **kwargs)
                
                # Add rate limit headers
                if isinstance(response, Response):
                    # Parse limit string (e.g., "20/minute")
                    limit_parts = limit.split("/")
                    limit_value = limit_parts[0] if limit_parts else "100"
                    
                    response.headers["X-RateLimit-Limit"] = limit_value
                    response.headers["X-RateLimit-Remaining"] = "N/A"  # Would need limiter state
                    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
                
                return response
            except RateLimitExceeded as e:
                # Handle rate limit exceeded
                from services.logging_service import logger
                from exceptions import RateLimitError
                
                request = kwargs.get("request") or kwargs.get("http_request")
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                if request:
                    user_id = getattr(request.state, "user_id", None)
                    logger.log_security_event(
                        event_type="rate_limit_exceeded",
                        user_id=user_id,
                        ip_address=get_remote_address(request),
                        details={"endpoint": request.url.path, "limit": limit}
                    )
                
                limit_parts = limit.split("/")
                limit_value = limit_parts[0] if limit_parts else "100"
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "type": "RateLimitError",
                            "message": "Rate limit exceeded. Please try again later.",
                            "code": "RATE_LIMIT_ERROR",
                            "details": {
                                "limit": limit,
                                "retry_after": 60
                            }
                        }
                    },
                    headers={
                        "X-RateLimit-Limit": limit_value,
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + 60),
                        "Retry-After": "60"
                    }
                )
        
        return wrapper
    return decorator

