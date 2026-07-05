"""
Unit tests for FeedbackService
"""

import pytest
from services.feedback_service import FeedbackService
from exceptions import DatabaseError, NotFoundError


@pytest.mark.asyncio
async def test_create_feedback(test_db_session, mock_user_id):
    """Test creating feedback"""
    service = FeedbackService()
    
    feedback = service.create_feedback(
        user_id=mock_user_id,
        category="bug",
        title="Test Bug",
        message="This is a test bug report",
        db=test_db_session,
        priority="high"
    )
    
    assert feedback["user_id"] == mock_user_id
    assert feedback["category"] == "bug"
    assert feedback["title"] == "Test Bug"
    assert feedback["status"] == "open"
    assert feedback["priority"] == "high"
    assert "id" in feedback


@pytest.mark.asyncio
async def test_create_feedback_with_metadata(test_db_session, mock_user_id):
    """Test creating feedback with metadata"""
    service = FeedbackService()
    
    metadata = {"browser": "Chrome", "version": "1.0.0"}
    feedback = service.create_feedback(
        user_id=mock_user_id,
        category="feature",
        title="Feature Request",
        message="Add new feature",
        db=test_db_session,
        metadata=metadata
    )
    
    assert feedback["metadata"] == metadata


@pytest.mark.asyncio
async def test_get_feedback(test_db_session, mock_user_id):
    """Test getting feedback by ID"""
    service = FeedbackService()
    
    # Create feedback first
    created = service.create_feedback(
        user_id=mock_user_id,
        category="question",
        title="Test Question",
        message="How do I use this?",
        db=test_db_session
    )
    
    # Get feedback
    feedback = service.get_feedback(
        feedback_id=created["id"],
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert feedback is not None
    assert feedback["id"] == created["id"]
    assert feedback["title"] == "Test Question"


@pytest.mark.asyncio
async def test_get_feedback_not_found(test_db_session, mock_user_id):
    """Test getting non-existent feedback"""
    service = FeedbackService()
    
    feedback = service.get_feedback(
        feedback_id=99999,
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert feedback is None


@pytest.mark.asyncio
async def test_get_feedback_unauthorized(test_db_session, mock_user_id):
    """Test getting feedback from different user"""
    service = FeedbackService()
    
    # Create feedback for user1
    created = service.create_feedback(
        user_id=mock_user_id,
        category="bug",
        title="User1 Bug",
        message="Bug report",
        db=test_db_session
    )
    
    # Try to get with different user
    feedback = service.get_feedback(
        feedback_id=created["id"],
        user_id="different_user",
        db=test_db_session
    )
    
    assert feedback is None


@pytest.mark.asyncio
async def test_get_user_feedback(test_db_session, mock_user_id):
    """Test getting all feedback for a user"""
    service = FeedbackService()
    
    # Create multiple feedback entries
    for i in range(3):
        service.create_feedback(
            user_id=mock_user_id,
            category="bug",
            title=f"Bug {i}",
            message=f"Bug report {i}",
            db=test_db_session
        )
    
    # Get all feedback
    feedbacks = service.get_user_feedback(
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert len(feedbacks) == 3
    assert all(f["user_id"] == mock_user_id for f in feedbacks)


@pytest.mark.asyncio
async def test_get_user_feedback_filtered_by_status(test_db_session, mock_user_id):
    """Test getting feedback filtered by status"""
    service = FeedbackService()
    
    # Create feedback
    feedback1 = service.create_feedback(
        user_id=mock_user_id,
        category="bug",
        title="Bug 1",
        message="Bug report 1",
        db=test_db_session
    )
    
    # Update status
    service.update_feedback_status(
        feedback_id=feedback1["id"],
        user_id=mock_user_id,
        status="resolved",
        db=test_db_session
    )
    
    # Create another with open status
    service.create_feedback(
        user_id=mock_user_id,
        category="bug",
        title="Bug 2",
        message="Bug report 2",
        db=test_db_session
    )
    
    # Get only open feedback
    open_feedbacks = service.get_user_feedback(
        user_id=mock_user_id,
        db=test_db_session,
        status="open"
    )
    
    assert len(open_feedbacks) == 1
    assert open_feedbacks[0]["status"] == "open"


@pytest.mark.asyncio
async def test_update_feedback_status(test_db_session, mock_user_id):
    """Test updating feedback status"""
    service = FeedbackService()
    
    # Create feedback
    feedback = service.create_feedback(
        user_id=mock_user_id,
        category="bug",
        title="Test Bug",
        message="Bug report",
        db=test_db_session
    )
    
    # Update status
    result = service.update_feedback_status(
        feedback_id=feedback["id"],
        user_id=mock_user_id,
        status="in_progress",
        response="We're working on it",
        db=test_db_session
    )
    
    assert result is True
    
    # Verify update
    updated = service.get_feedback(
        feedback_id=feedback["id"],
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert updated["status"] == "in_progress"
    assert updated["response"] == "We're working on it"


@pytest.mark.asyncio
async def test_update_feedback_status_not_found(test_db_session, mock_user_id):
    """Test updating non-existent feedback"""
    service = FeedbackService()
    
    result = service.update_feedback_status(
        feedback_id=99999,
        user_id=mock_user_id,
        status="resolved",
        db=test_db_session
    )
    
    assert result is False


@pytest.mark.asyncio
async def test_create_feedback_database_error(test_db_session, mock_user_id):
    """Test handling database errors"""
    service = FeedbackService()
    
    # Close session to cause error
    test_db_session.close()
    
    with pytest.raises(DatabaseError):
        service.create_feedback(
            user_id=mock_user_id,
            category="bug",
            title="Test",
            message="Test",
            db=test_db_session
        )
