"""
Pytest configuration and fixtures for backend tests
"""

import pytest
import os
import sys
from pathlib import Path
from typing import Generator
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from models.database import Base, TrackingEntryDB, UserContextDB, UserDB, TaskDB
from dependencies.database import get_db
from config.settings import get_settings


# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_postpartum.db"


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing"""
    # Set test mode
    os.environ["TEST_MODE"] = "true"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    return get_settings()


@pytest.fixture(scope="session")
def test_engine(test_settings):
    """Create test database engine"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    # Clean up test database file
    if os.path.exists("./test_postpartum.db"):
        os.remove("./test_postpartum.db")


@pytest.fixture(scope="function")
def test_db_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session"""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_user_id():
    """Generate a mock user ID for testing"""
    return "test_user_123"


@pytest.fixture
def sample_tracking_entry(mock_user_id):
    """Create a sample tracking entry for testing"""
    from models.schemas import TrackingEntry, EntryType, FeedingType
    
    return TrackingEntry(
        user_id=mock_user_id,
        entry_type=EntryType.FEEDING,
        feeding_type=FeedingType.BREAST,
        duration_minutes=20,
        amount_ml=100
    )


@pytest.fixture
def sample_user_context(mock_user_id):
    """Create sample user context for testing"""
    return {
        "baby_age_days": 10,
        "birth_type": "vaginal",
        "feeding_type": "breast",
        "sleep_hours_avg": 3
    }


@pytest.fixture
def mock_ai_response():
    """Create a mock AI response for testing"""
    return {
        "text": "This is a test AI response",
        "suggestions": ["Suggestion 1", "Suggestion 2"],
        "red_flags": [],
        "provider": "test",
        "validation": {
            "safety_score": 0.9,
            "confidence": 0.85
        }
    }


@pytest.fixture
def reset_container():
    """Reset service container for testing"""
    from dependencies.container import reset_container, get_container
    
    # Reset before test
    reset_container()
    container = get_container()
    
    yield container
    
    # Clean up after test
    reset_container()


@pytest.fixture
def mock_cache():
    """Create a mock cache for testing"""
    from services.cache_service import CacheService
    return CacheService()


@pytest.fixture(autouse=True)
def cleanup_test_data(test_db_session):
    """Clean up test data after each test"""
    yield
    # Clean up all test data
    test_db_session.query(TrackingEntryDB).delete()
    test_db_session.query(UserContextDB).delete()
    test_db_session.query(UserDB).delete()
    test_db_session.query(TaskDB).delete()
    test_db_session.commit()
