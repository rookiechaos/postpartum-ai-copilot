"""
Database Dependencies - FastAPI dependency injection for database sessions
Database dependencies - FastAPI dependency injection for database sessions
"""

from typing import Generator
from sqlalchemy.orm import Session
from models.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session
    
    Usage:
        @app.get("/items")
        async def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session (for non-FastAPI contexts)
    
    Note: Caller is responsible for closing the session
    """
    return SessionLocal()
