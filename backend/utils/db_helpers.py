"""
Database Helper Utilities - Common database query patterns and error handling
"""

import asyncio
from typing import Callable, TypeVar, Any, Optional
from sqlalchemy.orm import Session
from exceptions import DatabaseError, ValidationError, ConflictError, NotFoundError

T = TypeVar('T')


async def query_in_executor(
    func: Callable[[], T],
    db: Session,
    error_message: Optional[str] = None
) -> T:
    """
    Execute a blocking database query in an executor thread
    
    Args:
        func: Synchronous function that performs database operations
        db: Database session
        error_message: Custom error message (optional)
        
    Returns:
        Result from the function
        
    Raises:
        DatabaseError: If the query fails
    """
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, func)
    except (ValidationError, ConflictError, NotFoundError):
        # Expected care validation/access conflicts must remain actionable 4xx
        # responses, rather than appearing to clients as uncertain server writes.
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_msg = error_message or f"Database query failed: {str(e)}"
        raise DatabaseError(error_msg) from e


async def execute_with_rollback(
    func: Callable[[], T],
    db: Session,
    error_message: Optional[str] = None
) -> T:
    """
    Execute a database operation with automatic rollback on error
    
    This is a synchronous version for operations that don't need executor
    
    Args:
        func: Function that performs database operations
        db: Database session
        error_message: Custom error message (optional)
        
    Returns:
        Result from the function
        
    Raises:
        DatabaseError: If the operation fails
    """
    try:
        return func()
    except Exception as e:
        db.rollback()
        error_msg = error_message or f"Database operation failed: {str(e)}"
        raise DatabaseError(error_msg) from e


def safe_query(
    query_func: Callable[[], T],
    db: Session,
    error_message: Optional[str] = None
) -> Optional[T]:
    """
    Execute a database query safely with error handling
    
    Args:
        query_func: Function that returns a query result
        db: Database session
        error_message: Custom error message (optional)
        
    Returns:
        Query result or None if query fails
        
    Note:
        This function catches exceptions and returns None instead of raising.
        Use this when you want to handle errors gracefully.
    """
    try:
        return query_func()
    except Exception as e:
        db.rollback()
        if error_message:
            from services.logging_service import logger
            logger.log_error(e, context={"action": "safe_query", "error_message": error_message})
        return None

