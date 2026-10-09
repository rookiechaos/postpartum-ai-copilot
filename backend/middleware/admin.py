"""
Admin Middleware - Check if user is admin
"""

from fastapi import Depends, HTTPException, status
from typing import List
from models.schemas import User
from middleware.auth import get_current_user
from config.settings import get_settings
from services.logging_service import logger


def get_admin_emails() -> List[str]:
    """
    Get list of admin emails from settings
    
    Returns:
        List of admin email addresses
    """
    settings = get_settings()
    # Get from environment variable ADMIN_EMAILS (comma-separated)
    admin_emails_str = getattr(settings, 'admin_emails', None)
    if admin_emails_str:
        return [email.strip().lower() for email in admin_emails_str.split(",") if email.strip()]
    
    # Default admin emails (for development)
    # In production, these should be set via environment variable
    return []


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require admin access
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    admin_emails = get_admin_emails()
    
    if not admin_emails:
        # If no admin emails configured, log warning and deny access
        logger.log_info(
            "Admin check: No admin emails configured, denying access",
            context={"user_id": current_user.user_id, "email": current_user.email}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. No admin users configured."
        )
    
    user_email = current_user.email.lower()
    
    if user_email not in admin_emails:
        logger.log_info(
            "Admin check: User is not admin",
            context={"user_id": current_user.user_id, "email": current_user.email}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user

