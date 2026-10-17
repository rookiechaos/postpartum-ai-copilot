"""
Unit tests for TrackingService
"""

import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from services.tracking_service import TrackingService
from models.schemas import TrackingEntry, EntryType, FeedingType


@pytest.mark.asyncio
async def test_add_entry(test_db_session, sample_tracking_entry):
    """Test adding a tracking entry"""
    service = TrackingService()
    
    result = await service.add_entry(sample_tracking_entry, test_db_session)
    
    assert result["message"] == "Entry added successfully"
    assert "id" in result
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_get_entries(test_db_session, mock_user_id, sample_tracking_entry):
    """Test getting tracking entries"""
    service = TrackingService()
    
    # Add an entry first
    await service.add_entry(sample_tracking_entry, test_db_session)
    
    # Get entries
    entries = await service.get_entries(mock_user_id, test_db_session, days=7)
    
    assert len(entries) > 0
    assert entries[0]["user_id"] == mock_user_id
    assert entries[0]["entry_type"] == "feeding"


@pytest.mark.asyncio
async def test_get_user_context(test_db_session, mock_user_id):
    """Test getting user context"""
    service = TrackingService()
    
    context = await service.get_user_context(mock_user_id, test_db_session)
    
    assert isinstance(context, dict)
    assert "baby_age_days" in context
    assert "birth_type" in context


@pytest.mark.asyncio
async def test_update_user_context(test_db_session, mock_user_id, sample_user_context):
    """Test updating user context"""
    service = TrackingService()
    
    result = await service.update_user_context(
        mock_user_id,
        sample_user_context,
        test_db_session
    )
    
    assert result["message"] == "Context updated successfully"
    assert result["context"] == sample_user_context
    
    # Verify it was saved
    context = await service.get_user_context(mock_user_id, test_db_session)
    assert context["baby_age_days"] == 10


@pytest.mark.asyncio
async def test_get_weight_trends(test_db_session, mock_user_id):
    """Test getting weight trends"""
    service = TrackingService()
    
    # Create weight entries
    from models.database import TrackingEntryDB
    for i in range(5):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="recovery",
            weight_kg=70.0 - (i * 0.5),  # Gradual weight loss
            timestamp=datetime.utcnow() - timedelta(days=4-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    trends = await service.get_weight_trends(mock_user_id, test_db_session)
    
    assert isinstance(trends, list)
    assert len(trends) > 0
    assert "weight_kg" in trends[0]
    assert "timestamp" in trends[0]


@pytest.mark.asyncio
async def test_get_weight_trends_no_data(test_db_session, mock_user_id):
    """Test getting weight trends with no data"""
    service = TrackingService()
    
    trends = await service.get_weight_trends(mock_user_id, test_db_session)
    
    assert isinstance(trends, list)
    assert len(trends) == 0


@pytest.mark.asyncio
async def test_get_recovery_trends(test_db_session, mock_user_id):
    """Test getting recovery trends"""
    service = TrackingService()
    
    # Create recovery entries
    from models.database import TrackingEntryDB
    for i in range(3):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="recovery",
            breast_condition="normal" if i % 2 == 0 else "engorged",
            recovery_notes=f"Day {i} recovery notes",
            timestamp=datetime.utcnow() - timedelta(days=2-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    trends = await service.get_recovery_trends(mock_user_id, test_db_session)
    
    assert isinstance(trends, list)
    assert len(trends) > 0
    assert "breast_condition" in trends[0] or "recovery_notes" in trends[0]
    assert "timestamp" in trends[0]


@pytest.mark.asyncio
async def test_get_recovery_trends_no_data(test_db_session, mock_user_id):
    """Test getting recovery trends with no data"""
    service = TrackingService()
    
    trends = await service.get_recovery_trends(mock_user_id, test_db_session)
    
    assert isinstance(trends, list)
    assert len(trends) == 0


@pytest.mark.asyncio
async def test_generate_daily_summary(test_db_session, mock_user_id):
    """Test generating daily summary"""
    service = TrackingService()
    
    # Create some tracking entries for today
    from models.database import TrackingEntryDB
    for i in range(3):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="feeding",
            timestamp=datetime.utcnow() - timedelta(hours=3-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    summary = await service.generate_daily_summary(
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert isinstance(summary, dict)
    assert "date" in summary
    assert "entries_count" in summary
    assert "summary" in summary and "record_counts" in summary


@pytest.mark.asyncio
async def test_calendar_summaries_ignore_legacy_ai_argument(test_db_session, mock_user_id):
    """A read must not send profile/record information even if a legacy caller supplies AI."""
    from models.database import TrackingEntryDB
    instant = datetime(2026, 10, 16, 3)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.replace(tzinfo=timezone.utc).astimezone(tz) if tz else instant

        @classmethod
        def utcnow(cls):
            return instant

    for _ in range(3):
        test_db_session.add(TrackingEntryDB(user_id=mock_user_id, entry_type="feeding", timestamp=instant))
    test_db_session.add(TrackingEntryDB(user_id="other_review_account", entry_type="mood", timestamp=instant,
                                       mood_notes="private-note-marker"))
    test_db_session.commit()
    service = TrackingService()
    ai = SimpleNamespace(generate_tracking_summary=AsyncMock())
    with patch("services.tracking_service.datetime", FrozenDatetime):
        daily = await service.generate_daily_summary(mock_user_id, test_db_session, ai_service=ai)
        weekly = await service.generate_weekly_summary(mock_user_id, test_db_session, ai_service=ai)
    assert daily["date"] == "2026-10-16"
    assert weekly["week_start"] == "2026-10-12"
    assert daily["record_counts"] == weekly["record_counts"] == {"feeding": 3}
    ai.generate_tracking_summary.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_weekly_summary(test_db_session, mock_user_id):
    """Test generating weekly summary"""
    service = TrackingService()
    
    # Create tracking entries for the week
    from models.database import TrackingEntryDB
    for i in range(7):
        entry = TrackingEntryDB(
            user_id=mock_user_id,
            entry_type="feeding",
            timestamp=datetime.utcnow() - timedelta(days=6-i)
        )
        test_db_session.add(entry)
    test_db_session.commit()
    
    summary = await service.generate_weekly_summary(
        user_id=mock_user_id,
        db=test_db_session
    )
    
    assert isinstance(summary, dict)
    assert "week_start" in summary or "period" in summary
    assert "entries_count" in summary or "total_entries" in summary
    assert "summary" in summary and "record_counts" in summary


@pytest.mark.asyncio
async def test_add_recovery_tracking(test_db_session, mock_user_id):
    """Test adding recovery tracking entry"""
    service = TrackingService()
    
    from models.schemas import RecoveryEntry
    recovery_entry = RecoveryEntry(
        user_id=mock_user_id,
        weight_kg=70.0,
        breast_condition="normal",
        recovery_notes="Feeling good today"
    )
    
    result = await service.add_recovery_tracking(recovery_entry, test_db_session)
    
    assert "message" in result
    assert "id" in result
    assert result["message"] == "Recovery entry added successfully"
