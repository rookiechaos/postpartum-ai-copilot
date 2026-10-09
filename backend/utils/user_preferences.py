"""
User Preferences Utilities - Common functions for user preferences
"""

from typing import Optional
from sqlalchemy.orm import Session
from services.tracking_service import TrackingService
from services.logging_service import logger


async def get_user_language_preference(
    user_id: Optional[str],
    db: Session,
    default: str = "en"
) -> str:
    """
    Get user language preference from user context with caching
    
    Args:
        user_id: User ID (optional)
        db: Database session
        default: Default language if not found
        
    Returns:
        Language code (e.g., "en", "ja", "zh")
    """
    if not user_id:
        return default
    
    # Check cache first
    from services.cache_service import get_cache
    cache = get_cache()
    cache_key = f"user_language:{user_id}"
    cached_language = cache.get(cache_key)
    if cached_language is not None:
        return cached_language
    
    try:
        tracking_service = TrackingService()
        context = await tracking_service.get_user_context(user_id, db)
        language = context.get("language", default) or default
        
        # Cache the result (TTL: 1 hour)
        # Language preference doesn't change frequently, so longer TTL is acceptable
        cache.set(cache_key, language, ttl=3600)
        return language
    except Exception as e:
        logger.log_error(
            e,
            context={
                "action": "get_user_language_preference",
                "user_id": user_id
            }
        )
        # Return default on error
        return default


def invalidate_language_cache(user_id: str) -> None:
    """
    Invalidate cached language preference for a user
    
    Should be called when user updates their language preference
    
    Args:
        user_id: User ID
    """
    from services.cache_service import get_cache
    cache = get_cache()
    cache_key = f"user_language:{user_id}"
    cache.delete(cache_key)

