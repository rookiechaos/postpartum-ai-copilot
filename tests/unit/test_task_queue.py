"""
Unit tests for TaskQueue service
"""

import pytest
from datetime import datetime, timedelta
from services.task_queue import TaskQueue, TaskPriority, TaskStatus
from exceptions import TaskQueueError, NotFoundError


@pytest.mark.asyncio
async def test_create_task(test_db_session, mock_user_id):
    """Test creating a task"""
    queue = TaskQueue()
    
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test query"},
        user_id=mock_user_id,
        db=test_db_session,
        priority=TaskPriority.HIGH
    )
    
    assert task_id is not None
    assert isinstance(task_id, str)


@pytest.mark.asyncio
async def test_get_task(test_db_session, mock_user_id):
    """Test getting a task by ID"""
    queue = TaskQueue()
    
    # Create task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test query"},
        user_id=mock_user_id,
        db=test_db_session
    )
    
    # Get task
    task = queue.get_task(task_id, db=test_db_session)
    
    assert task is not None
    assert task["task_id"] == task_id
    assert task["task_type"] == "ai_chat"
    assert task["user_id"] == mock_user_id
    assert task["status"] == TaskStatus.PENDING.value


@pytest.mark.asyncio
async def test_get_task_not_found(test_db_session):
    """Test getting non-existent task"""
    queue = TaskQueue()
    
    task = queue.get_task("non_existent_id", db=test_db_session)
    
    assert task is None


@pytest.mark.asyncio
async def test_get_pending_tasks(test_db_session, mock_user_id):
    """Test getting pending tasks"""
    queue = TaskQueue()
    
    # Create multiple tasks
    task_ids = []
    for i in range(3):
        task_id = queue.create_task(
            task_type="ai_chat",
            task_data={"query": f"Query {i}"},
            user_id=mock_user_id,
            db=test_db_session,
            priority=TaskPriority.MEDIUM
        )
        task_ids.append(task_id)
    
    # Get pending tasks
    pending = queue.get_pending_tasks(db=test_db_session, limit=10)
    
    assert len(pending) >= 3
    assert all(t["status"] == TaskStatus.PENDING.value for t in pending)


@pytest.mark.asyncio
async def test_get_user_tasks(test_db_session, mock_user_id):
    """Test getting tasks for a specific user"""
    queue = TaskQueue()
    
    # Create tasks for user
    for i in range(2):
        queue.create_task(
            task_type="ai_chat",
            task_data={"query": f"Query {i}"},
            user_id=mock_user_id,
            db=test_db_session
        )
    
    # Create task for different user
    queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Other user query"},
        user_id="other_user",
        db=test_db_session
    )
    
    # Get user tasks
    user_tasks = queue.get_user_tasks(mock_user_id, db=test_db_session)
    
    assert len(user_tasks) == 2
    assert all(t["user_id"] == mock_user_id for t in user_tasks)


@pytest.mark.asyncio
async def test_claim_task(test_db_session, mock_user_id):
    """Test claiming a task"""
    queue = TaskQueue()
    
    # Create task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test query"},
        user_id=mock_user_id,
        db=test_db_session
    )
    
    # Claim task
    worker_id = "worker_1"
    result = queue.claim_task(task_id, worker_id, db=test_db_session)
    
    assert result is True
    
    # Verify task is claimed
    task = queue.get_task(task_id, db=test_db_session)
    assert task["status"] == TaskStatus.PROCESSING.value
    assert task["worker_id"] == worker_id


@pytest.mark.asyncio
async def test_claim_task_already_claimed(test_db_session, mock_user_id):
    """Test claiming an already claimed task"""
    queue = TaskQueue()
    
    # Create and claim task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test query"},
        user_id=mock_user_id,
        db=test_db_session
    )
    
    queue.claim_task(task_id, "worker_1", db=test_db_session)
    
    # Try to claim again
    result = queue.claim_task(task_id, "worker_2", db=test_db_session)
    
    assert result is False


@pytest.mark.asyncio
async def test_update_task_status(test_db_session, mock_user_id):
    """Test updating task status"""
    queue = TaskQueue()
    
    # Create task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test query"},
        user_id=mock_user_id,
        db=test_db_session
    )
    
    # Update status
    queue.update_task_status(
        task_id=task_id,
        status=TaskStatus.COMPLETED,
        db=test_db_session,
        result={"response": "Test response"}
    )
    
    # Verify update
    task = queue.get_task(task_id, db=test_db_session)
    assert task["status"] == TaskStatus.COMPLETED.value
    assert task["result"] == {"response": "Test response"}


@pytest.mark.asyncio
async def test_cancel_task(test_db_session, mock_user_id):
    """Test canceling a task"""
    queue = TaskQueue()
    
    # Create task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test query"},
        user_id=mock_user_id,
        db=test_db_session
    )
    
    # Cancel task
    result = queue.cancel_task(task_id, mock_user_id, db=test_db_session)
    
    assert result is True
    
    # Verify cancellation
    task = queue.get_task(task_id, db=test_db_session)
    assert task["status"] == TaskStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_cancel_task_not_found(test_db_session, mock_user_id):
    """Test canceling non-existent task"""
    queue = TaskQueue()
    
    result = queue.cancel_task("non_existent_id", mock_user_id, db=test_db_session)
    
    assert result is False


@pytest.mark.asyncio
async def test_cancel_task_unauthorized(test_db_session, mock_user_id):
    """Test canceling task from different user"""
    queue = TaskQueue()
    
    # Create task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test query"},
        user_id=mock_user_id,
        db=test_db_session
    )
    
    # Try to cancel with different user
    result = queue.cancel_task(task_id, "other_user", db=test_db_session)
    
    assert result is False


@pytest.mark.asyncio
async def test_check_timeout_tasks(test_db_session, mock_user_id):
    """Test checking for timeout tasks"""
    queue = TaskQueue()
    
    # Create task with short timeout
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test query"},
        user_id=mock_user_id,
        db=test_db_session,
        timeout=1  # 1 second timeout
    )
    
    # Claim and set started_at to past
    queue.claim_task(task_id, "worker_1", db=test_db_session)
    
    # Manually set started_at to past
    from models.database import TaskDB
    task = test_db_session.query(TaskDB).filter(TaskDB.task_id == task_id).first()
    if task:
        task.started_at = datetime.utcnow() - timedelta(seconds=10)
        test_db_session.commit()
    
    # Check for timeouts
    timed_out = queue.check_timeout_tasks(db=test_db_session)
    
    assert task_id in timed_out
    
    # Verify task is marked as failed
    task = queue.get_task(task_id, db=test_db_session)
    assert task["status"] == TaskStatus.FAILED.value


@pytest.mark.asyncio
async def test_task_priority(test_db_session, mock_user_id):
    """Test task priority handling"""
    queue = TaskQueue()
    
    # Create tasks with different priorities
    high_task = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "High priority"},
        user_id=mock_user_id,
        db=test_db_session,
        priority=TaskPriority.HIGH
    )
    
    low_task = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Low priority"},
        user_id=mock_user_id,
        db=test_db_session,
        priority=TaskPriority.LOW
    )
    
    # Get pending tasks (should be ordered by priority)
    pending = queue.get_pending_tasks(db=test_db_session, limit=10)
    
    # High priority tasks should come first
    task_ids = [t["task_id"] for t in pending]
    assert task_ids.index(high_task) < task_ids.index(low_task)
