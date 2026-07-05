"""
Unit tests for AnalyticsService
"""

import pytest
from datetime import datetime, timedelta
from services.analytics_service import AnalyticsService
from services.task_queue import TaskQueue, TaskPriority
from models.database import TaskDB, TrackingEntryDB
from models.schemas import TrackingEntry, EntryType
from exceptions import DatabaseError


@pytest.mark.asyncio
async def test_get_user_usage_stats(test_db_session, mock_user_id):
    """Test getting user usage statistics"""
    service = AnalyticsService()
    
    # Create some tasks
    task_queue = TaskQueue()
    for i in range(5):
        task_queue.create_task(
            task_type="ai_chat",
            task_data={"query": f"Test query {i}"},
            user_id=mock_user_id,
            db=test_db_session,
            priority=TaskPriority.MEDIUM
        )
    
    # Create tracking entries
    from services.tracking_service import TrackingService
    tracking_service = TrackingService()
    
    for i in range(3):
        entry = TrackingEntry(
            user_id=mock_user_id,
            entry_type=EntryType.FEEDING,
            timestamp=datetime.utcnow() - timedelta(hours=i)
        )
        await tracking_service.add_entry(entry, test_db_session)
    
    # Get stats
    stats = service.get_user_usage_stats(
        user_id=mock_user_id,
        db=test_db_session,
        days=7
    )
    
    assert stats["user_id"] == mock_user_id
    assert "tasks" in stats
    assert "tracking" in stats
    assert stats["tasks"]["total"] == 5
    assert stats["tracking"]["total"] == 3


@pytest.mark.asyncio
async def test_get_system_stats(test_db_session, mock_user_id):
    """Test getting system-wide statistics"""
    service = AnalyticsService()
    
    # Create tasks for multiple users
    task_queue = TaskQueue()
    for user_id in [mock_user_id, "user2", "user3"]:
        for i in range(2):
            task_queue.create_task(
                task_type="ai_chat",
                task_data={"query": f"Query {i}"},
                user_id=user_id,
                db=test_db_session,
                priority=TaskPriority.MEDIUM
            )
    
    # Get system stats
    stats = service.get_system_stats(
        db=test_db_session,
        days=7
    )
    
    assert "period_days" in stats
    assert "tasks" in stats
    assert "task_types" in stats
    assert "top_users" in stats
    assert stats["tasks"]["total"] == 6


@pytest.mark.asyncio
async def test_get_task_performance_stats(test_db_session, mock_user_id):
    """Test getting task performance statistics"""
    service = AnalyticsService()
    
    # Create completed tasks with timing
    task_queue = TaskQueue()
    task_ids = []
    
    for i in range(3):
        task_id = task_queue.create_task(
            task_type="ai_chat",
            task_data={"query": f"Query {i}"},
            user_id=mock_user_id,
            db=test_db_session,
            priority=TaskPriority.MEDIUM
        )
        task_ids.append(task_id)
    
    # Simulate task completion with timing
    from models.database import TaskStatus
    for task_id in task_ids:
        task = test_db_session.query(TaskDB).filter(TaskDB.task_id == task_id).first()
        if task:
            task.status = TaskStatus.COMPLETED.value
            task.started_at = datetime.utcnow() - timedelta(seconds=10)
            task.completed_at = datetime.utcnow()
            test_db_session.commit()
    
    # Get performance stats
    stats = service.get_task_performance_stats(
        db=test_db_session,
        task_type="ai_chat",
        days=7
    )
    
    assert "task_type" in stats
    assert "total_tasks" in stats
    assert "completed_tasks" in stats
    assert "avg_processing_time_seconds" in stats
    assert stats["task_type"] == "ai_chat"
    assert stats["completed_tasks"] > 0


@pytest.mark.asyncio
async def test_get_task_performance_stats_no_completed_tasks(test_db_session):
    """Test performance stats with no completed tasks"""
    service = AnalyticsService()
    
    stats = service.get_task_performance_stats(
        db=test_db_session,
        days=7
    )
    
    assert stats["completed_tasks"] == 0
    assert stats["avg_processing_time_seconds"] == 0


@pytest.mark.asyncio
async def test_get_user_usage_stats_empty(test_db_session, mock_user_id):
    """Test getting stats for user with no activity"""
    service = AnalyticsService()
    
    stats = service.get_user_usage_stats(
        user_id=mock_user_id,
        db=test_db_session,
        days=7
    )
    
    assert stats["user_id"] == mock_user_id
    assert stats["tasks"]["total"] == 0
    assert stats["tracking"]["total"] == 0


@pytest.mark.asyncio
async def test_get_system_stats_empty(test_db_session):
    """Test getting system stats with no activity"""
    service = AnalyticsService()
    
    stats = service.get_system_stats(
        db=test_db_session,
        days=7
    )
    
    assert stats["tasks"]["total"] == 0
    assert stats["tasks"]["success_rate_percent"] == 0
