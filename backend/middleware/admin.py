"""
Admin Middleware - Check if user is admin
"""

from fastapi import Depends, HTTPException, status
from typing import List
from models.schemas import User
from middleware.auth import get_current_user
from config.settings import get_settings
from services.logging_service import logger


def get_admin_user_ids() -> List[str]:
    """Read administrator account IDs provisioned by the server operator."""
    settings = get_settings()
    configured = getattr(settings, "admin_user_ids", None) or ""
    return [user_id.strip() for user_id in configured.split(",") if user_id.strip()]


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
    if not current_user.is_active or current_user.user_id not in get_admin_user_ids():
        logger.log_info(
            "Admin check: User is not admin",
            context={"user_id": current_user.user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user

