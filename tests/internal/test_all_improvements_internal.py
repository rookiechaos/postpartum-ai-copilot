"""
Comprehensive Internal Test - Test all code improvements and features
Internal tests without exposing ports, run in product conda environment
"""

import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import os
import asyncio
from datetime import datetime

# Set test environment variables
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_internal_testing_only_min_32_chars")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_all_improvements.db")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("TEST_MODE", "True")
os.environ.setdefault("NSFW_DETECTION_ENABLED", "True")
os.environ.setdefault("NSFW_DETECTION_STRICT", "False")

from sqlalchemy.orm import Session
from models.database import SessionLocal, init_db, Base, engine
from dependencies.container import get_container
from config.settings import get_settings

# Register services in container (like main.py does)
def register_test_services():
    """Register services in container for testing"""
    container = get_container()
    
    def create_ai_service():
        from services.ai_service import AIService
        return AIService()
    
    def create_tracking_service():
        from services.tracking_service import TrackingService
        return TrackingService()
    
    def create_personalization_service():
        from services.personalization_service import PersonalizationService
        return PersonalizationService()
    
    def create_community_service():
        from services.community_service import CommunityService
        return CommunityService()
    
    def create_task_queue():
        from services.task_queue import TaskQueue
        return TaskQueue()
    
    def create_rag_service():
        from services.rag_service import RAGService
        if not get_settings().rag_enabled:
            return None
        try:
            return RAGService()
        except Exception:
            return None
    
    # Register services
    container.register_factory("ai_service", create_ai_service, singleton=True)
    container.register_factory("tracking_service", create_tracking_service, singleton=True)
    container.register_factory("personalization_service", create_personalization_service, singleton=True)
    container.register_factory("community_service", create_community_service, singleton=True)
    container.register_factory("task_queue", create_task_queue, singleton=True)
    container.register_factory("rag_service", create_rag_service, singleton=True)


def print_header(title: str):
    """Print test section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")


async def test_code_quality_improvements():
    """Test code quality improvements"""
    print_header("Code quality improvementsTesting (Code Quality Improvements)")
    
    results = []
    
    try:
        # Test 1: Database helpers
        print("\n1. Testing database helpers...")
        from utils.db_helpers import query_in_executor, execute_with_rollback, safe_query
        
        db = SessionLocal()
        try:
            def _test_query():
                return {"test": "data"}
            
            result = await query_in_executor(_test_query, db)
            assert result == {"test": "data"}
            print_test_result("query_in_executor", True)
            results.append(True)
        except Exception as e:
            print_test_result("query_in_executor", False, str(e))
            results.append(False)
        finally:
            db.close()
        
        # Test 2: Route files exist
        print("\n2. Testing route files...")
        route_files = [
            "api/chat_routes.py",
            "api/tracking_routes.py",
            "api/personalization_routes.py",
            "api/community_routes.py"
        ]
        
        for route_file in route_files:
            file_path = Path(__file__).resolve().parents[2] / "backend" / route_file
            exists = file_path.exists()
            print_test_result(f"Route file: {route_file}", exists)
            results.append(exists)
        
        # Test 3: Database indexes
        print("\n3. Testing database indexes...")
        from models.database import TrackingEntryDB, TaskDB, NotificationDB, FamilyMemberDB
        
        db = SessionLocal()
        try:
            # Check if indexes are defined
            tracking_indexes = TrackingEntryDB.__table_args__
            task_indexes = TaskDB.__table_args__
            notification_indexes = NotificationDB.__table_args__
            family_indexes = FamilyMemberDB.__table_args__
            
            has_indexes = (
                tracking_indexes is not None or
                task_indexes is not None or
                notification_indexes is not None or
                family_indexes is not None
            )
            print_test_result("Database composite indexes", has_indexes)
            results.append(has_indexes)
        except Exception as e:
            print_test_result("Database composite indexes", False, str(e))
            results.append(False)
        finally:
            db.close()
        
        # Test 4: Service container
        print("\n4. Testing service container...")
        container = get_container()
        
        services_to_test = [
            "ai_service",
            "tracking_service",
            "personalization_service",
            "community_service"
        ]
        
        for service_name in services_to_test:
            try:
                service = container.get(service_name)
                print_test_result(f"Service: {service_name}", service is not None)
                results.append(service is not None)
            except Exception as e:
                print_test_result(f"Service: {service_name}", False, str(e))
                results.append(False)
        
        # Test 5: Main.py size check
        print("\n5. Testing main.py refactoring...")
        main_file = Path(__file__).resolve().parents[2] / "backend" / "main.py"
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
            # main.py should be less than 300 lines after refactoring
            is_refactored = lines < 300
            print_test_result(f"main.py refactored (lines: {lines})", is_refactored)
            results.append(is_refactored)
        else:
            print_test_result("main.py refactored", False, "File not found")
            results.append(False)
        
        return all(results)
        
    except Exception as e:
        print(f"\n❌ Code quality improvements test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dependency_injection():
    """Test dependency injection improvements"""
    print_header("Dependency injection improvementsTesting (Dependency Injection)")
    
    results = []
    
    try:
        # Test 1: Community service in container
        print("\n1. Testing community service in container...")
        container = get_container()
        
        try:
            community_service = container.get("community_service")
            has_service = community_service is not None
            print_test_result("Community service in container", has_service)
            results.append(has_service)
        except Exception as e:
            print_test_result("Community service in container", False, str(e))
            results.append(False)
        
        # Test 2: Community routes use container
        print("\n2. Testing community routes use container...")
        try:
            from api.community_routes import container as route_container
            uses_container = route_container is not None
            print_test_result("Community routes use container", uses_container)
            results.append(uses_container)
        except Exception as e:
            print_test_result("Community routes use container", False, str(e))
            results.append(False)
        
        # Test 3: All services registered
        print("\n3. Testing all services registered...")
        container = get_container()
        required_services = [
            "ai_service",
            "tracking_service",
            "personalization_service",
            "task_queue",
            "rag_service",
            "community_service"
        ]
        
        for service_name in required_services:
            has_service = container.has(service_name)
            print_test_result(f"Service registered: {service_name}", has_service)
            results.append(has_service)
        
        return all(results)
        
    except Exception as e:
        print(f"\n❌ Dependency injection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_community_features():
    """Test community features"""
    print_header("Community featuresTesting (Community Features)")
    
    results = []
    
    try:
        # Test 1: Community models
        print("\n1. Testing community models...")
        from models.community_models import (
            PostDB, CommentDB, PostLikeDB, PostFavoriteDB, UserFollowDB
        )
        
        models_exist = all([
            PostDB is not None,
            CommentDB is not None,
            PostLikeDB is not None,
            PostFavoriteDB is not None,
            UserFollowDB is not None
        ])
        print_test_result("Community models exist", models_exist)
        results.append(models_exist)
        
        # Test 2: Community service
        print("\n2. Testing community service...")
        from services.community_service import CommunityService
        
        service = CommunityService()
        has_service = service is not None
        print_test_result("Community service exists", has_service)
        results.append(has_service)
        
        # Test 3: Community routes
        print("\n3. Testing community routes...")
        try:
            from api.community_routes import router
            has_routes = router is not None
            print_test_result("Community routes exist", has_routes)
            results.append(has_routes)
        except Exception as e:
            print_test_result("Community routes exist", False, str(e))
            results.append(False)
        
        # Test 4: NSFW detector integration
        print("\n4. Testing NSFW detector integration...")
        try:
            from services.nsfw_detector import get_nsfw_detector
            detector = get_nsfw_detector()
            has_detector = detector is not None
            print_test_result("NSFW detector integrated", has_detector)
            results.append(has_detector)
        except Exception as e:
            print_test_result("NSFW detector integrated", False, str(e))
            results.append(False)
        
        # Test 5: Database operations
        print("\n5. Testing database operations...")
        db = SessionLocal()
        try:
            # Test creating a post (without committing)
            from models.community_models import PostDB
            import uuid
            
            test_post = PostDB(
                post_id=f"test_{uuid.uuid4().hex[:12]}",
                user_id="test_user",
                title="Test Post",
                content="Test content",
                category="test"
            )
            db.add(test_post)
            db.flush()  # Test insert without committing
            
            # Rollback
            db.rollback()
            
            print_test_result("Database operations work", True)
            results.append(True)
        except Exception as e:
            print_test_result("Database operations work", False, str(e))
            results.append(False)
        finally:
            db.close()
        
        return all(results)
        
    except Exception as e:
        print(f"\n❌ Community features test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration():
    """Test integration of all improvements"""
    print_header("Integration tests (Integration Tests)")
    
    results = []
    
    try:
        # Test 1: Service container with all services
        print("\n1. Testing service container integration...")
        container = get_container()
        
        # Get all services
        services = {}
        service_names = [
            "ai_service",
            "tracking_service",
            "personalization_service",
            "community_service"
        ]
        
        for service_name in service_names:
            try:
                services[service_name] = container.get(service_name)
                print_test_result(f"Get {service_name}", True)
                results.append(True)
            except Exception as e:
                print_test_result(f"Get {service_name}", False, str(e))
                results.append(False)
        
        # Test 2: Routes can import services
        print("\n2. Testing routes can import services...")
        try:
            from api.community_routes import container as comm_container
            from api.tracking_routes import container as track_container
            from api.chat_routes import container as chat_container
            
            all_containers_work = (
                comm_container is not None and
                track_container is not None and
                chat_container is not None
            )
            print_test_result("Routes can import services", all_containers_work)
            results.append(all_containers_work)
        except Exception as e:
            print_test_result("Routes can import services", False, str(e))
            results.append(False)
        
        # Test 3: Database helpers work with services
        print("\n3. Testing database helpers with services...")
        from utils.db_helpers import query_in_executor
        
        db = SessionLocal()
        try:
            def _test_db_helper():
                return {"status": "ok"}
            
            result = await query_in_executor(_test_db_helper, db)
            works = result == {"status": "ok"}
            print_test_result("Database helpers work with services", works)
            results.append(works)
        except Exception as e:
            print_test_result("Database helpers work with services", False, str(e))
            results.append(False)
        finally:
            db.close()
        
        return all(results)
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("\n" + "="*70)
    print("  Comprehensive Code Improvements Internal Tests")
    print("  Comprehensive Code Improvements Internal Test")
    print("="*70)
    print(f"Test date: {datetime.now().isoformat()}")
    print(f"Test environment: product conda environment")
    print(f"Test type: internal (no exposed ports)")
    print("="*70)
    
    # Setup
    print("\nInitializing test environment...")
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
    
    # Register services
    print("Registering services in container...")
    try:
        register_test_services()
        print("✅ Services registered successfully")
    except Exception as e:
        print(f"⚠️  Service registration warning: {e}")
    
    # Run tests
    test_results = []
    
    # Test 1: Code quality improvements
    result1 = await test_code_quality_improvements()
    test_results.append(("Code quality improvements", result1))
    
    # Test 2: Dependency injection
    result2 = await test_dependency_injection()
    test_results.append(("Dependency injection improvements", result2))
    
    # Test 3: Community features
    result3 = await test_community_features()
    test_results.append(("Community features", result3))
    
    # Test 4: Integration
    result4 = await test_integration()
    test_results.append(("Integration tests", result4))
    
    # Summary
    print_header("Test Summary")
    
    print("\nTest results:")
    total_passed = 0
    total_tests = len(test_results)
    
    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {test_name}")
        if passed:
            total_passed += 1
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n" + "="*70)
        print("  ✅ All tests passed!")
        print("="*70)
        return 0
    else:
        print("\n" + "="*70)
        print(f"  ⚠️  {total_tests - total_passed} test(s) failed")
        print("="*70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


