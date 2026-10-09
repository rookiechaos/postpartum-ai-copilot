"""
Utility functions for common operations
"""

__all__ = ["get_user_language_preference"]


def __getattr__(name):
    # Loading settings or storage helpers must not eagerly import database services.
    if name == "get_user_language_preference":
        from .user_preferences import get_user_language_preference
        return get_user_language_preference
    raise AttributeError(name)

