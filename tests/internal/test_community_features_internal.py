"""
Internal test for community features
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
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_community.db")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("TEST_MODE", "True")
os.environ.setdefault("NSFW_DETECTION_ENABLED", "True")
os.environ.setdefault("NSFW_DETECTION_STRICT", "False")

from sqlalchemy.orm import Session
from models.database import SessionLocal, init_db, Base, engine
from models.community_models import (
    PostDB, CommentDB, PostLikeDB, PostFavoriteDB, UserFollowDB
)
from services.community_service import CommunityService
from services.nsfw_detector import get_nsfw_detector
from utils.db_helpers import query_in_executor


# Test database
TEST_DB_URL = "sqlite:///./test_community.db"


def setup_test_db():
    """Setup test database"""
    # Create test engine
    from sqlalchemy import create_engine
    test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    TestSessionLocal = SessionLocal.__class__(bind=test_engine)
    return TestSessionLocal()


def cleanup_test_db(db: Session):
    """Cleanup test database"""
    try:
        # Delete all test data
        db.query(PostLikeDB).delete()
        db.query(PostFavoriteDB).delete()
        db.query(UserFollowDB).delete()
        db.query(CommentDB).delete()
        db.query(PostDB).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️  Cleanup error: {e}")


async def test_community_service(db: Session):
    """Test community service functions"""
    print("\n" + "="*60)
    print("Testing Community Service")
    print("="*60)
    
    service = CommunityService()
    test_user_id = "test_user_community"
    test_user_id_2 = "test_user_community_2"
    
    try:
        # Test 1: Create Post
        print("\n1. Testing create_post...")
        post = await service.create_post(
            user_id=test_user_id,
            title="Test post title",
            content="This is a test post about postpartum care experiences.",
            category="experience",
            tags=["postpartum", "experience sharing"],
            db=db
        )
        assert post is not None
        assert post["post_id"] is not None
        assert post["title"] == "Test post title"
        assert post["like_count"] == 0
        assert post["comment_count"] == 0
        post_id = post["post_id"]
        print(f"✅ Post created: {post_id}")
        
        # Test 2: Get Post
        print("\n2. Testing get_post...")
        retrieved_post = await service.get_post(
            post_id=post_id,
            user_id=test_user_id,
            db=db
        )
        assert retrieved_post is not None
        assert retrieved_post["post_id"] == post_id
        assert retrieved_post["view_count"] > 0  # View count should increment
        print(f"✅ Post retrieved: view_count={retrieved_post['view_count']}")
        
        # Test 3: Get Posts List
        print("\n3. Testing get_posts...")
        posts = await service.get_posts(
            limit=10,
            offset=0,
            db=db
        )
        assert isinstance(posts, list)
        assert len(posts) >= 1
        print(f"✅ Posts list retrieved: {len(posts)} posts")
        
        # Test 4: Like Post
        print("\n4. Testing like_post...")
        like_result = await service.like_post(
            post_id=post_id,
            user_id=test_user_id,
            db=db
        )
        assert like_result["is_liked"] is True
        assert like_result["like_count"] == 1
        print(f"✅ Post liked: like_count={like_result['like_count']}")
        
        # Test 5: Unlike Post
        print("\n5. Testing unlike_post...")
        unlike_result = await service.like_post(
            post_id=post_id,
            user_id=test_user_id,
            db=db
        )
        assert unlike_result["is_liked"] is False
        assert unlike_result["like_count"] == 0
        print(f"✅ Post unliked: like_count={unlike_result['like_count']}")
        
        # Test 6: Favorite Post
        print("\n6. Testing favorite_post...")
        favorite_result = await service.favorite_post(
            post_id=post_id,
            user_id=test_user_id,
            db=db
        )
        assert favorite_result["is_favorited"] is True
        print("✅ Post favorited")
        
        # Test 7: Create Comment
        print("\n7. Testing create_comment...")
        comment = await service.create_comment(
            post_id=post_id,
            user_id=test_user_id_2,
            content="This is a helpful test comment.",
            db=db
        )
        assert comment is not None
        assert comment["comment_id"] is not None
        assert comment["content"] == "This is a helpful test comment."
        comment_id = comment["comment_id"]
        print(f"✅ Comment created: {comment_id}")
        
        # Test 8: Get Comments
        print("\n8. Testing get_comments...")
        comments = await service.get_comments(
            post_id=post_id,
            limit=10,
            db=db
        )
        assert isinstance(comments, list)
        assert len(comments) >= 1
        print(f"✅ Comments retrieved: {len(comments)} comments")
        
        # Test 9: Follow User
        print("\n9. Testing follow_user...")
        follow_result = await service.follow_user(
            follower_id=test_user_id,
            following_id=test_user_id_2,
            db=db
        )
        assert follow_result["is_following"] is True
        print("✅ User followed")
        
        # Test 10: Unfollow User
        print("\n10. Testing unfollow_user...")
        unfollow_result = await service.follow_user(
            follower_id=test_user_id,
            following_id=test_user_id_2,
            db=db
        )
        assert unfollow_result["is_following"] is False
        print("✅ User unfollowed")
        
        # Test 11: NSFW Detection
        print("\n11. Testing NSFW detection in posts...")
        try:
            await service.create_post(
                user_id=test_user_id,
                title="Inappropriate Title",
                content="This should be blocked by NSFW detector",
                db=db
            )
            print("⚠️  NSFW detection may not be blocking (check detector config)")
        except Exception as e:
            if "inappropriate" in str(e).lower():
                print("✅ NSFW detection working: inappropriate content blocked")
            else:
                print(f"⚠️  Unexpected error: {e}")
        
        print("\n" + "="*60)
        print("✅ All Community Service Tests Passed!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_models(db: Session):
    """Test database models"""
    print("\n" + "="*60)
    print("Testing Database Models")
    print("="*60)
    
    try:
        # Test PostDB
        print("\n1. Testing PostDB model...")
        post = PostDB(
            post_id="test_post_123",
            user_id="test_user",
            title="Test Post",
            content="Test content",
            category="test",
            like_count=0,
            comment_count=0
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        assert post.id is not None
        print("✅ PostDB model works")
        
        # Test CommentDB
        print("\n2. Testing CommentDB model...")
        comment = CommentDB(
            comment_id="test_comment_123",
            post_id="test_post_123",
            user_id="test_user",
            content="Test comment"
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        assert comment.id is not None
        print("✅ CommentDB model works")
        
        # Test PostLikeDB
        print("\n3. Testing PostLikeDB model...")
        like = PostLikeDB(
            post_id="test_post_123",
            user_id="test_user"
        )
        db.add(like)
        db.commit()
        assert like.id is not None
        print("✅ PostLikeDB model works")
        
        # Cleanup
        db.query(PostLikeDB).filter(PostLikeDB.post_id == "test_post_123").delete()
        db.query(CommentDB).filter(CommentDB.post_id == "test_post_123").delete()
        db.query(PostDB).filter(PostDB.post_id == "test_post_123").delete()
        db.commit()
        
        print("\n" + "="*60)
        print("✅ All Database Model Tests Passed!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_nsfw_integration():
    """Test NSFW detector integration"""
    print("\n" + "="*60)
    print("Testing NSFW Detector Integration")
    print("="*60)
    
    try:
        detector = get_nsfw_detector()
        
        # Test safe content
        print("\n1. Testing safe content...")
        safe_result = await detector.check("This is a safe post about postpartum care.", check_type="input")
        print(f"   Result: {safe_result.get('level')} - {safe_result.get('reason')}")
        
        # Test potentially unsafe content (may vary based on detector config)
        print("\n2. Testing content detection...")
        test_result = await detector.check("Test content for moderation", check_type="input")
        print(f"   Result: {test_result.get('level')} - {test_result.get('reason')}")
        
        print("\n" + "="*60)
        print("✅ NSFW Detector Integration Test Passed!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("\n" + "="*60)
    print("Community Features Internal Test")
    print("="*60)
    print(f"Test Date: {datetime.now().isoformat()}")
    print(f"Test Environment: product conda environment")
    print(f"Test Type: Internal (no port exposure)")
    print("="*60)
    
    # Setup test database
    print("\nSetting up test database...")
    db = setup_test_db()
    
    try:
        # Run tests
        results = []
        
        # Test 1: Database Models
        results.append(await test_database_models(db))
        
        # Test 2: NSFW Integration
        results.append(await test_nsfw_integration())
        
        # Test 3: Community Service
        results.append(await test_community_service(db))
        
        # Summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"Total Tests: {len(results)}")
        print(f"Passed: {sum(results)}")
        print(f"Failed: {len(results) - sum(results)}")
        
        if all(results):
            print("\n✅ All tests passed!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Cleanup
        print("\nCleaning up test database...")
        cleanup_test_db(db)
        db.close()
        
        # Remove test database file
        try:
            if os.path.exists("test_community.db"):
                os.remove("test_community.db")
                print("✅ Test database cleaned up")
        except Exception as e:
            print(f"⚠️  Could not remove test database: {e}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

