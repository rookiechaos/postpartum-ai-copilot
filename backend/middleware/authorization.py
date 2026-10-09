"""
Authorization Middleware - Ensure users can only access their own data
"""

from fastapi import HTTPException, status
from models.schemas import User
from exceptions import NotFoundError


def check_user_authorization(
    current_user: User,
    resource_user_id: str,
    resource_name: str = "resource"
) -> None:
    """
    Check if current user is authorized to access a resource
    
    Args:
        current_user: Current authenticated user
        resource_user_id: User ID that owns the resource
        resource_name: Name of the resource (for error message)
    
    Raises:
        HTTPException: If user is not authorized
    """
    if current_user.user_id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to access this {resource_name}"
        )


def check_user_authorization_optional(
    current_user: User,
    resource_user_id: str,
    resource_name: str = "resource"
) -> bool:
    """
    Check if current user is authorized to access a resource (returns bool)
    
    Args:
        current_user: Current authenticated user
        resource_user_id: User ID that owns the resource
        resource_name: Name of the resource (for error message)
    
    Returns:
        True if authorized, False otherwise
    """
    return current_user.user_id == resource_user_id

