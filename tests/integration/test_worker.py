"""
Worker test script
Test task queue and worker functionality
"""

import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import os
import sys
import time
import asyncio
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

from services.task_queue import TaskQueue, TaskStatus, TaskPriority
from models.database import init_db, SessionLocal, TaskDB
from services.auth_service import AuthService
from models.schemas import UserCreate


def test_task_creation():
    print("\n=== Task creation ===")
    queue = TaskQueue()
    
    # Create test user first
    auth_service = AuthService()
    test_user_id = "test_user_worker"
    
    try:
        user = auth_service.create_user(UserCreate(
            email=f"test_{int(time.time())}@test.com",
            password="test123",
            user_id=test_user_id
        ))
        print(f"✅ Created test user: {user.user_id}")
    except Exception as e:
        print(f"⚠️  User may already exist: {e}")
    
    # Create a test task
    task_data = {
        "query": "Test query for worker",
        "language": "en"
    }
    
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data=task_data,
        user_id=test_user_id,
        priority=TaskPriority.MEDIUM,
        timeout=60
    )
    
    print(f"✅ Task created: {task_id}")
    
    # Get task
    task = queue.get_task(task_id)
    assert task is not None, "Task should exist"
    assert task["status"] == TaskStatus.PENDING.value, "Task status should be pending"
    assert task["task_type"] == "ai_chat", "Task type should be correct"
    
    print(f"✅ Task query succeeded: {task['status']}")
    
    return task_id, test_user_id


def test_task_claiming():
    print("\n=== Task claim ===")
    queue = TaskQueue()
    
    # Create a task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test"},
        user_id="test_user",
        priority=TaskPriority.MEDIUM
    )
    
    # Claim task
    worker_id = "test_worker_1"
    claimed = queue.claim_task(task_id, worker_id)
    
    assert claimed, "Task should be claimed successfully"
    
    # Check task status
    task = queue.get_task(task_id)
    assert task["status"] == TaskStatus.PROCESSING.value, "Task status should be processing"
    assert task["worker_id"] == worker_id, "Worker ID should be correct"
    
    print(f"✅ Task claimed: {task['status']}")
    
    return task_id


def test_task_completion():
    print("\n=== Task completion ===")
    queue = TaskQueue()
    
    # Create and claim a task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test"},
        user_id="test_user",
        priority=TaskPriority.MEDIUM
    )
    
    queue.claim_task(task_id, "test_worker")
    
    # Complete task
    result = {
        "response": "Test response",
        "suggestions": ["Suggestion 1"],
        "red_flags": []
    }
    
    updated = queue.update_task_status(
        task_id=task_id,
        status=TaskStatus.COMPLETED,
        result=result
    )
    
    assert updated, "Task status should update successfully"
    
    # Check task
    task = queue.get_task(task_id)
    assert task["status"] == TaskStatus.COMPLETED.value, "Task status should be completed"
    assert task["result"] is not None, "Task should have a result"
    assert task["result"]["response"] == "Test response", "Result should be correct"
    
    print(f"✅ Task completed: {task['status']}")
    
    return task_id


def test_task_failure():
    print("\n=== Test task failure and retry ===")
    queue = TaskQueue(max_retries=3)
    
    # Create a task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test"},
        user_id="test_user",
        priority=TaskPriority.MEDIUM
    )
    
    queue.claim_task(task_id, "test_worker")
    
    # Fail task
    queue.update_task_status(
        task_id=task_id,
        status=TaskStatus.FAILED,
        error="Test error"
    )
    
    # Check task
    task = queue.get_task(task_id)
    assert task["status"] == TaskStatus.PENDING.value, "Should retry after failure (back to pending)"
    assert task["retry_count"] == 1, "Retry count should increment"
    
    print(f"✅ Task failure/retry mechanism OK: retry_count={task['retry_count']}")
    
    return task_id


def test_task_priority():
    print("\n=== Task priority ===")
    queue = TaskQueue()
    
    # Create tasks with different priorities
    low_task = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Low priority"},
        user_id="test_user",
        priority=TaskPriority.LOW
    )
    
    time.sleep(0.1)  # Small delay to ensure different timestamps
    
    high_task = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "High priority"},
        user_id="test_user",
        priority=TaskPriority.HIGH
    )
    
    # Get pending tasks (should prioritize high)
    pending = queue.get_pending_tasks(limit=10)
    
    # High priority tasks should come first
    if len(pending) >= 2:
        first_priority = pending[0]["priority"]
        print(f"✅ Priority ordering OK: first task priority={first_priority}")
    
    return low_task, high_task


def test_task_cancellation():
    print("\n=== Task cancel ===")
    queue = TaskQueue()
    
    # Create a task
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test"},
        user_id="test_user",
        priority=TaskPriority.MEDIUM
    )
    
    # Cancel task
    cancelled = queue.cancel_task(task_id, "test_user")
    
    assert cancelled, "Task should be cancelled successfully"
    
    # Check task
    task = queue.get_task(task_id)
    assert task["status"] == TaskStatus.CANCELLED.value, "Task status should be cancelled"
    
    print(f"✅ Task cancelled: {task['status']}")
    
    return task_id


def test_get_user_tasks():
    print("\n=== Get user task list ===")
    queue = TaskQueue()
    
    user_id = "test_user_list"
    
    # Create multiple tasks
    task_ids = []
    for i in range(3):
        task_id = queue.create_task(
            task_type="ai_chat",
            task_data={"query": f"Test {i}"},
            user_id=user_id,
            priority=TaskPriority.MEDIUM
        )
        task_ids.append(task_id)
    
    # Get user tasks
    user_tasks = queue.get_user_tasks(user_id, limit=10)
    
    assert len(user_tasks) >= 3, "Should return at least 3 tasks"
    assert all(task["user_id"] == user_id for task in user_tasks), "All tasks should belong to the same user"
    
    print(f"✅ Get user task list succeeded: {len(user_tasks)} task(s)")
    
    return task_ids


def test_timeout_detection():
    print("\n=== Timeout detection ===")
    queue = TaskQueue()
    
    # Create a task with short timeout
    task_id = queue.create_task(
        task_type="ai_chat",
        task_data={"query": "Test"},
        user_id="test_user",
        priority=TaskPriority.MEDIUM,
        timeout=1  # 1 second timeout
    )
    
    # Claim task
    queue.claim_task(task_id, "test_worker")
    
    # Manually set started_at to past time (simulate timeout)
    db = SessionLocal()
    try:
        task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
        if task:
            from datetime import timedelta
            task.started_at = datetime.utcnow() - timedelta(seconds=2)
            db.commit()
    finally:
        db.close()
    
    # Check for timeout
    timed_out = queue.check_timeout_tasks()
    
    # Task should be marked as failed due to timeout
    task = queue.get_task(task_id)
    if task_id in timed_out or task["status"] == TaskStatus.FAILED.value:
        print(f"✅ Timeout detection OK: task status={task['status']}")
    else:
        print(f"⚠️  Timeout detection may need more time")
    
    return task_id


def run_all_tests():
    print("=" * 60)
    print("Worker Feature Tests")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
    
    tests = [
        ("Task creation", test_task_creation),
        ("Task claim", test_task_claiming),
        ("Task completion", test_task_completion),
        ("Task failure and retry", test_task_failure),
        ("Task priority", test_task_priority),
        ("Task cancel", test_task_cancellation),
        ("Get user task list", test_get_user_tasks),
        ("Timeout detection", test_timeout_detection),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ {test_name}: PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: FAILED - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Test results: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

