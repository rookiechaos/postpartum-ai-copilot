#!/usr/bin/env python3
"""
Internal Test Script - Tests service layer without exposing ports
"""

import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Set test mode
os.environ["TEST_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_internal.db"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from exceptions import (
    PostpartumException,
    AuthenticationError,
    ValidationError,
    AIServiceError,
    DatabaseError,
    TaskQueueError,
    NotFoundError,
    AuthorizationError,
    ConflictError,
    ServiceUnavailableError,
    RateLimitError
)
from middleware.error_handler import (
    postpartum_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from unittest.mock import Mock


class InternalTester:
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
        
    def test(self, name: str, func):
        try:
            result = func()
            if result is not False:
                self.passed += 1
                self.test_results.append(("PASS", name))
                print(f"✅ {name}")
                return True
            else:
                self.failed += 1
                self.test_results.append(("FAIL", name))
                print(f"❌ {name}")
                return False
        except Exception as e:
            self.failed += 1
            self.test_results.append(("FAIL", name, str(e)))
            print(f"❌ {name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def print_summary(self):
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"PASSED: {self.passed}")
        print(f"FAILED: {self.failed}")
        print(f"Total: {self.passed + self.failed}")
        print("=" * 60)
        
        if self.failed > 0:
            print("\nFailed tests:")
            for result in self.test_results:
                if result[0] == "FAIL":
                    print(f"  - {result[1]}")
                    if len(result) > 2:
                        print(f"    Error: {result[2]}")


def test_exceptions():
    tester = InternalTester()
    
    tester.test("PostpartumException basic functionality", lambda: (
        exc := PostpartumException("Test", "TEST", {"key": "value"}),
        exc.message == "Test" and exc.error_code == "TEST" and exc.details == {"key": "value"}
    )[1])
    
    tester.test("AuthenticationError", lambda: (
        exc := AuthenticationError("Auth failed"),
        exc.error_code == "AUTH_ERROR"
    )[1])
    
    tester.test("ValidationError", lambda: (
        exc := ValidationError("Invalid input"),
        exc.error_code == "VALIDATION_ERROR"
    )[1])
    
    tester.test("AIServiceError", lambda: (
        exc := AIServiceError("AI unavailable"),
        exc.error_code == "AI_SERVICE_ERROR"
    )[1])
    
    tester.test("DatabaseError", lambda: (
        exc := DatabaseError("DB connection failed"),
        exc.error_code == "DATABASE_ERROR"
    )[1])
    
    tester.test("TaskQueueError", lambda: (
        exc := TaskQueueError("Task failed"),
        exc.error_code == "TASK_QUEUE_ERROR"
    )[1])
    
    tester.test("NotFoundError", lambda: (
        exc := NotFoundError("Not found"),
        exc.error_code == "NOT_FOUND_ERROR"
    )[1])
    
    tester.test("AuthorizationError", lambda: (
        exc := AuthorizationError("Unauthorized"),
        exc.error_code == "AUTHORIZATION_ERROR"
    )[1])
    
    tester.test("ConflictError", lambda: (
        exc := ConflictError("Conflict"),
        exc.error_code == "CONFLICT_ERROR"
    )[1])
    
    tester.test("ServiceUnavailableError", lambda: (
        exc := ServiceUnavailableError("Service down"),
        exc.error_code == "SERVICE_UNAVAILABLE"
    )[1])
    
    tester.test("RateLimitError", lambda: (
        exc := RateLimitError("Rate limit exceeded"),
        exc.error_code == "RATE_LIMIT_ERROR"
    )[1])
    
    tester.print_summary()
    return tester.failed == 0


def test_error_handler():
    import asyncio
    
    tester = InternalTester()
    
    async def run_handler_tests():
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.state.user_id = "test_user"
        
        # Testing PostpartumException handler
        exc = NotFoundError("Resource not found")
        response = await postpartum_exception_handler(request, exc)
        tester.test("NotFoundError returns 404", lambda: response.status_code == 404)
        
        exc = AuthenticationError("Auth failed")
        response = await postpartum_exception_handler(request, exc)
        tester.test("AuthenticationError returns 401", lambda: response.status_code == 401)
        
        exc = AuthorizationError("Unauthorized")
        response = await postpartum_exception_handler(request, exc)
        tester.test("AuthorizationError returns 403", lambda: response.status_code == 403)
        
        exc = ConflictError("Conflict")
        response = await postpartum_exception_handler(request, exc)
        tester.test("ConflictError returns 409", lambda: response.status_code == 409)
        
        exc = RateLimitError("Rate limit")
        response = await postpartum_exception_handler(request, exc)
        tester.test("RateLimitError returns 429", lambda: response.status_code == 429)
        
        exc = ServiceUnavailableError("Service down")
        response = await postpartum_exception_handler(request, exc)
        tester.test("ServiceUnavailableError returns 503", lambda: response.status_code == 503)
        
        validation_error = RequestValidationError([{"loc": ["body", "field"], "msg": "required", "type": "value_error"}])
        response = await validation_exception_handler(request, validation_error)
        tester.test("ValidationException returns 422", lambda: response.status_code == 422)
        
        # Testing HTTP exception handler
        http_exc = StarletteHTTPException(status_code=404, detail="Not found")
        response = await http_exception_handler(request, http_exc)
        tester.test("HTTPException handler", lambda: response.status_code == 404)
        
        general_exc = Exception("General error")
        response = await general_exception_handler(request, general_exc)
        tester.test("GeneralException returns 500", lambda: response.status_code == 500)
    
    asyncio.run(run_handler_tests())
    tester.print_summary()
    return tester.failed == 0


def test_services():
    engine = create_engine("sqlite:///./test_internal.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    tester = InternalTester()
    
    try:
        # Testing FeedbackService
        from services.feedback_service import FeedbackService
        feedback_service = FeedbackService()
        
        feedback = feedback_service.create_feedback(
            user_id="test_user_1",
            category="bug",
            title="Test bug",
            message="This is a test bug report",
            db=db,
            priority="high"
        )
        tester.test("FeedbackService.create_feedback", lambda: feedback["user_id"] == "test_user_1" and feedback["category"] == "bug")
        
        retrieved = feedback_service.get_feedback(feedback["id"], "test_user_1", db)
        tester.test("FeedbackService.get_feedback", lambda: retrieved is not None and retrieved["id"] == feedback["id"])
        
        user_feedbacks = feedback_service.get_user_feedback("test_user_1", db)
        tester.test("FeedbackService.get_user_feedback", lambda: len(user_feedbacks) > 0)
        
        try:
            feedback_service.create_feedback(
                user_id="test_user_1",
                category="invalid_category",
                title="Test",
                message="Test",
                db=db
            )
            tester.test("FeedbackService validation failed", False)
        except (DatabaseError, ValidationError):
            tester.test("FeedbackService validation failed", True)
        
        # Testing TaskQueue
        from services.task_queue import TaskQueue
        task_queue = TaskQueue()
        
        task_id = task_queue.create_task(
            task_type="chat",
            task_data={"query": "test"},
            user_id="test_user_1",
            db=db
        )
        tester.test("TaskQueue.create_task", lambda: task_id is not None)
        
        task = task_queue.get_task(task_id, db)
        tester.test("TaskQueue.get_task", lambda: task is not None and task["task_id"] == task_id)
        
        user_tasks = task_queue.get_user_tasks("test_user_1", db)
        tester.test("TaskQueue.get_user_tasks", lambda: len(user_tasks) > 0)
        
        # Testing NotFoundError
        try:
            task_queue.get_task("nonexistent_task_id", db)
            tester.test("TaskQueue NotFoundError", False)
        except NotFoundError:
            tester.test("TaskQueue NotFoundError", True)
        except:
            # If NotFoundError not raised, check returns None
            task = task_queue.get_task("nonexistent_task_id", db)
            tester.test("TaskQueue NotFoundError", task is None)
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_internal.db"):
            os.remove("./test_internal.db")
    
    tester.print_summary()
    return tester.failed == 0


def test_configuration():
    tester = InternalTester()
    
    from config.settings import get_settings
    settings = get_settings()
    
    tester.test("Settings object exists", lambda: settings is not None)
    tester.test("Settings has test_mode attribute", lambda: hasattr(settings, "test_mode"))
    tester.test("Settings has database_url attribute", lambda: hasattr(settings, "database_url"))
    
    tester.print_summary()
    return tester.failed == 0


def main():
    print("=" * 60)
    print("Internal Testing Started")
    print("=" * 60)
    print()
    
    results = []
    
    print("\n[1/4]Testing Exceptions")
    print("-" * 60)
    results.append(("Exceptions", test_exceptions()))
    
    print("\n[2/4]Testing Error Handlers")
    print("-" * 60)
    results.append(("Error handlers", test_error_handler()))
    
    print("\n[3/4]Testing Services")
    print("-" * 60)
    results.append(("Services", test_services()))
    
    print("\n[4/4]Testing Configuration")
    print("-" * 60)
    results.append(("Configuration", test_configuration()))
    
    print("\n" + "=" * 60)
    print("Final Test Results")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉All tests passed!")
        return 0
    else:
        print("\n⚠️Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())


