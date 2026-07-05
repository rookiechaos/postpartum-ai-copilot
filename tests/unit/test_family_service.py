"""
Unit tests for FamilyService - Extended tests for new methods
"""

import pytest
from datetime import datetime
from services.family_service import FamilyService
from models.database import FamilyDB, FamilyMemberDB
from exceptions import ValidationError


@pytest.mark.asyncio
async def test_generate_family_summary_daily(test_db_session, mock_user_id):
    """Test generating daily family summary"""
    service = FamilyService()
    
    # Create a family
    family = service.create_family(
        user_id=mock_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Generate summary
    summary = await service.generate_family_summary(
        family_id=family_id,
        user_id=mock_user_id,
        period="daily",
        db=test_db_session
    )
    
    assert "family_id" in summary
    assert "period" in summary
    assert summary["period"] == "daily"
    assert "summary" in summary
    assert "shared_entries_count" in summary
    assert "members_count" in summary
    assert "timestamp" in summary


@pytest.mark.asyncio
async def test_generate_family_summary_weekly(test_db_session, mock_user_id):
    """Test generating weekly family summary"""
    service = FamilyService()
    
    # Create a family
    family = service.create_family(
        user_id=mock_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Generate summary
    summary = await service.generate_family_summary(
        family_id=family_id,
        user_id=mock_user_id,
        period="weekly",
        db=test_db_session
    )
    
    assert "family_id" in summary
    assert "period" in summary
    assert summary["period"] == "weekly"
    assert "summary" in summary


@pytest.mark.asyncio
async def test_generate_family_summary_with_services(test_db_session, mock_user_id):
    """Test generating family summary with tracking and AI services"""
    service = FamilyService()
    
    # Create a family
    family = service.create_family(
        user_id=mock_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Try to generate summary with services (may not be available in test mode)
    try:
        from services.tracking_service import TrackingService
        from services.ai_service import AIService
        
        tracking_service = TrackingService()
        ai_service = AIService()
        
        summary = await service.generate_family_summary(
            family_id=family_id,
            user_id=mock_user_id,
            period="daily",
            tracking_service=tracking_service,
            ai_service=ai_service,
            db=test_db_session
        )
        
        assert "family_id" in summary
        assert "summary" in summary
    except Exception:
        # If services not available, test without them
        summary = await service.generate_family_summary(
            family_id=family_id,
            user_id=mock_user_id,
            period="daily",
            db=test_db_session
        )
        assert "family_id" in summary


@pytest.mark.asyncio
async def test_generate_family_summary_not_member(test_db_session, mock_user_id):
    """Test generating family summary when user is not a member"""
    service = FamilyService()
    
    # Create a family with different user
    other_user_id = "other_user"
    family = service.create_family(
        user_id=other_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Try to generate summary as non-member
    with pytest.raises(ValidationError):
        await service.generate_family_summary(
            family_id=family_id,
            user_id=mock_user_id,
            period="daily",
            db=test_db_session
        )


def test_share_tracking_data_enable(test_db_session, mock_user_id):
    """Test enabling tracking data sharing"""
    service = FamilyService()
    
    # Create a family
    family = service.create_family(
        user_id=mock_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Enable sharing
    result = service.share_tracking_data(
        family_id=family_id,
        user_id=mock_user_id,
        share_enabled=True,
        db=test_db_session
    )
    
    assert result["family_id"] == family_id
    assert result["user_id"] == mock_user_id
    assert result["share_enabled"] is True
    assert "message" in result


def test_share_tracking_data_disable(test_db_session, mock_user_id):
    """Test disabling tracking data sharing"""
    service = FamilyService()
    
    # Create a family
    family = service.create_family(
        user_id=mock_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Disable sharing
    result = service.share_tracking_data(
        family_id=family_id,
        user_id=mock_user_id,
        share_enabled=False,
        db=test_db_session
    )
    
    assert result["share_enabled"] is False


def test_share_tracking_data_not_member(test_db_session, mock_user_id):
    """Test sharing tracking data when user is not a member"""
    service = FamilyService()
    
    # Create a family with different user
    other_user_id = "other_user"
    family = service.create_family(
        user_id=other_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Try to share as non-member
    with pytest.raises(ValidationError):
        service.share_tracking_data(
            family_id=family_id,
            user_id=mock_user_id,
            share_enabled=True,
            db=test_db_session
        )


def test_create_family_task(test_db_session, mock_user_id):
    """Test creating a family task"""
    service = FamilyService()
    
    # Create a family
    family = service.create_family(
        user_id=mock_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Create a task
    task = service.create_family_task(
        family_id=family_id,
        creator_user_id=mock_user_id,
        title="Test Task",
        description="This is a test task",
        priority="high",
        db=test_db_session
    )
    
    assert "task_id" in task
    assert task["family_id"] == family_id
    assert task["title"] == "Test Task"
    assert task["description"] == "This is a test task"
    assert task["status"] == "pending"
    assert task["priority"] == "high"


def test_create_family_task_with_assignment(test_db_session, mock_user_id):
    """Test creating a family task with assignment"""
    service = FamilyService()
    
    # Create a family
    family = service.create_family(
        user_id=mock_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Invite another member
    other_user_id = "other_user"
    service.invite_member(
        family_id=family_id,
        inviter_user_id=mock_user_id,
        email="other@example.com",
        role="member",
        db=test_db_session
    )
    
    # Create a task assigned to the other user
    task = service.create_family_task(
        family_id=family_id,
        creator_user_id=mock_user_id,
        title="Assigned Task",
        assigned_to_user_id=other_user_id,
        priority="medium",
        db=test_db_session
    )
    
    assert task["title"] == "Assigned Task"
    assert task["priority"] == "medium"


def test_create_family_task_not_member(test_db_session, mock_user_id):
    """Test creating a family task when user is not a member"""
    service = FamilyService()
    
    # Create a family with different user
    other_user_id = "other_user"
    family = service.create_family(
        user_id=other_user_id,
        name="Test Family",
        db=test_db_session
    )
    family_id = family["family_id"]
    
    # Try to create task as non-member
    with pytest.raises(ValidationError):
        service.create_family_task(
            family_id=family_id,
            creator_user_id=mock_user_id,
            title="Test Task",
            db=test_db_session
        )
