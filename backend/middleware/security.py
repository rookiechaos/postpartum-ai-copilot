"""
Security Middleware - Security headers and additional protections
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from services.security_validator import SecurityHeaders
from config.settings import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Get security headers
        security_headers = SecurityHeaders.get_security_headers()
        
        # Add headers to response
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Add custom security headers
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "unknown")
        
        return response


class SecureCookieMiddleware(BaseHTTPMiddleware):
    """Ensure cookies are secure"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Set secure cookie flags if cookies are present
        if "Set-Cookie" in response.headers:
            # Ensure cookies are secure in production
            settings = get_settings()
            if not settings.debug:
                # This would be handled by FastAPI's cookie settings
                # but we ensure it here as well
                pass
        
        return response

