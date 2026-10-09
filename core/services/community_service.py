"""
Community Service - Handles community features (posts, comments, likes, follows)
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from models.community_models import (
    PostDB, CommentDB, PostLikeDB, CommentLikeDB,
    PostFavoriteDB, UserFollowDB, TopicDB, PostTopicDB, PostReportDB
)
from services.nsfw_detector import get_nsfw_detector
from services.logging_service import logger
from exceptions import DatabaseError, ValidationError, NotFoundError
from utils.db_helpers import query_in_executor, execute_with_rollback


class CommunityService:
    """Service for community features"""
    
    def __init__(self):
        self.nsfw_detector = get_nsfw_detector()
    
    async def create_post(
        self,
        user_id: str,
        title: str,
        content: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        images: Optional[List[str]] = None,
        is_anonymous: bool = False,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create a new post
        
        Args:
            user_id: User ID
            title: Post title
            content: Post content
            category: Post category
            tags: List of tags
            images: List of image URLs
            is_anonymous: Whether post is anonymous
            db: Database session
            
        Returns:
            Created post data
        """
        if not db:
            raise DatabaseError("Database session required")
        
        # NSFW detection
        title_check = await self.nsfw_detector.check(title, check_type="input")
        content_check = await self.nsfw_detector.check(content, check_type="input")
        
        if self.nsfw_detector.should_block(title_check) or self.nsfw_detector.should_block(content_check):
            raise ValidationError("Post contains inappropriate content")
        
        # Determine moderation status
        moderation_status = "approved"
        if title_check.get("level") == "suspicious" or content_check.get("level") == "suspicious":
            moderation_status = "pending"
        
        def _create_post():
            post_id = f"post_{uuid.uuid4().hex[:16]}"
            post = PostDB(
                post_id=post_id,
                user_id=user_id,
                title=title,
                content=content,
                category=category,
                tags=tags or [],
                images=images or [],
                is_anonymous=is_anonymous,
                moderation_status=moderation_status
            )
            db.add(post)
            db.commit()
            db.refresh(post)
            return post
        
        post = await query_in_executor(
            _create_post,
            db,
            error_message="Failed to create post"
        )
        
        return self._post_to_dict(post)
    
    async def get_posts(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        topic_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",  # created_at, like_count, comment_count
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Get posts list
        
        Args:
            user_id: Filter by user ID (optional)
            category: Filter by category (optional)
            topic_id: Filter by topic (optional)
            limit: Number of posts to return
            offset: Offset for pagination
            sort_by: Sort field
            db: Database session
            
        Returns:
            List of posts
        """
        if not db:
            raise DatabaseError("Database session required")
        
        def _get_posts():
            query = db.query(PostDB).filter(PostDB.is_deleted == False)
            
            if user_id:
                query = query.filter(PostDB.user_id == user_id)
            
            if category:
                query = query.filter(PostDB.category == category)
            
            if topic_id:
                # Join with post_topics
                query = query.join(PostTopicDB).filter(PostTopicDB.topic_id == topic_id)
            
            # Filter by moderation status
            query = query.filter(PostDB.moderation_status == "approved")
            
            # Sort
            if sort_by == "like_count":
                query = query.order_by(desc(PostDB.like_count), desc(PostDB.created_at))
            elif sort_by == "comment_count":
                query = query.order_by(desc(PostDB.comment_count), desc(PostDB.created_at))
            else:
                query = query.order_by(desc(PostDB.created_at))
            
            posts = query.offset(offset).limit(limit).all()
            return [self._post_to_dict(post) for post in posts]
        
        return await query_in_executor(
            _get_posts,
            db,
            error_message="Failed to get posts"
        )
    
    async def get_post(
        self,
        post_id: str,
        user_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get a single post by ID
        
        Args:
            post_id: Post ID
            user_id: User ID (for checking like/favorite status)
            db: Database session
            
        Returns:
            Post data with user interaction status
        """
        if not db:
            raise DatabaseError("Database session required")
        
        def _get_post():
            post = db.query(PostDB).filter(
                and_(
                    PostDB.post_id == post_id,
                    PostDB.is_deleted == False
                )
            ).first()
            
            if not post:
                return None
            
            # Increment view count
            post.view_count += 1
            db.commit()
            db.refresh(post)
            
            post_dict = self._post_to_dict(post)
            
            # Add user interaction status
            if user_id:
                # Check if user liked
                like = db.query(PostLikeDB).filter(
                    and_(
                        PostLikeDB.post_id == post_id,
                        PostLikeDB.user_id == user_id
                    )
                ).first()
                post_dict["is_liked"] = like is not None
                
                # Check if user favorited
                favorite = db.query(PostFavoriteDB).filter(
                    and_(
                        PostFavoriteDB.post_id == post_id,
                        PostFavoriteDB.user_id == user_id
                    )
                ).first()
                post_dict["is_favorited"] = favorite is not None
            else:
                post_dict["is_liked"] = False
                post_dict["is_favorited"] = False
            
            return post_dict
        
        result = await query_in_executor(
            _get_post,
            db,
            error_message="Failed to get post"
        )
        
        if not result:
            raise NotFoundError(f"Post {post_id} not found")
        
        return result
    
    async def like_post(
        self,
        post_id: str,
        user_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Like or unlike a post
        
        Args:
            post_id: Post ID
            user_id: User ID
            db: Database session
            
        Returns:
            Updated like status and count
        """
        if not db:
            raise DatabaseError("Database session required")
        
        def _toggle_like():
            # Check if post exists
            post = db.query(PostDB).filter(
                and_(
                    PostDB.post_id == post_id,
                    PostDB.is_deleted == False
                )
            ).first()
            
            if not post:
                return None
            
            # Check if already liked
            existing_like = db.query(PostLikeDB).filter(
                and_(
                    PostLikeDB.post_id == post_id,
                    PostLikeDB.user_id == user_id
                )
            ).first()
            
            if existing_like:
                # Unlike
                db.delete(existing_like)
                post.like_count = max(0, post.like_count - 1)
                is_liked = False
            else:
                # Like
                like = PostLikeDB(
                    post_id=post_id,
                    user_id=user_id
                )
                db.add(like)
                post.like_count += 1
                is_liked = True
            
            db.commit()
            db.refresh(post)
            
            return {
                "is_liked": is_liked,
                "like_count": post.like_count
            }
        
        result = await query_in_executor(
            _toggle_like,
            db,
            error_message="Failed to toggle like"
        )
        
        if not result:
            raise NotFoundError(f"Post {post_id} not found")
        
        return result
    
    async def favorite_post(
        self,
        post_id: str,
        user_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Favorite or unfavorite a post
        
        Args:
            post_id: Post ID
            user_id: User ID
            db: Database session
            
        Returns:
            Updated favorite status
        """
        if not db:
            raise DatabaseError("Database session required")
        
        def _toggle_favorite():
            # Check if post exists
            post = db.query(PostDB).filter(
                and_(
                    PostDB.post_id == post_id,
                    PostDB.is_deleted == False
                )
            ).first()
            
            if not post:
                return None
            
            # Check if already favorited
            existing_favorite = db.query(PostFavoriteDB).filter(
                and_(
                    PostFavoriteDB.post_id == post_id,
                    PostFavoriteDB.user_id == user_id
                )
            ).first()
            
            if existing_favorite:
                # Unfavorite
                db.delete(existing_favorite)
                is_favorited = False
            else:
                # Favorite
                favorite = PostFavoriteDB(
                    post_id=post_id,
                    user_id=user_id
                )
                db.add(favorite)
                is_favorited = True
            
            db.commit()
            
            return {
                "is_favorited": is_favorited
            }
        
        result = await query_in_executor(
            _toggle_favorite,
            db,
            error_message="Failed to toggle favorite"
        )
        
        if not result:
            raise NotFoundError(f"Post {post_id} not found")
        
        return result
    
    async def create_comment(
        self,
        post_id: str,
        user_id: str,
        content: str,
        parent_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create a comment on a post
        
        Args:
            post_id: Post ID
            user_id: User ID
            content: Comment content
            parent_id: Parent comment ID (for replies)
            db: Database session
            
        Returns:
            Created comment data
        """
        if not db:
            raise DatabaseError("Database session required")
        
        # NSFW detection
        content_check = await self.nsfw_detector.check(content, check_type="input")
        if self.nsfw_detector.should_block(content_check):
            raise ValidationError("Comment contains inappropriate content")
        
        def _create_comment():
            # Check if post exists
            post = db.query(PostDB).filter(
                and_(
                    PostDB.post_id == post_id,
                    PostDB.is_deleted == False
                )
            ).first()
            
            if not post:
                return None
            
            comment_id = f"comment_{uuid.uuid4().hex[:16]}"
            comment = CommentDB(
                comment_id=comment_id,
                post_id=post_id,
                user_id=user_id,
                content=content,
                parent_id=parent_id,
                moderation_status="approved" if content_check.get("level") == "safe" else "pending"
            )
            db.add(comment)
            
            # Update post comment count
            post.comment_count += 1
            db.commit()
            db.refresh(comment)
            
            return self._comment_to_dict(comment)
        
        result = await query_in_executor(
            _create_comment,
            db,
            error_message="Failed to create comment"
        )
        
        if not result:
            raise NotFoundError(f"Post {post_id} not found")
        
        return result
    
    async def get_comments(
        self,
        post_id: str,
        limit: int = 50,
        offset: int = 0,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Get comments for a post
        
        Args:
            post_id: Post ID
            limit: Number of comments to return
            offset: Offset for pagination
            db: Database session
            
        Returns:
            List of comments
        """
        if not db:
            raise DatabaseError("Database session required")
        
        def _get_comments():
            comments = db.query(CommentDB).filter(
                and_(
                    CommentDB.post_id == post_id,
                    CommentDB.is_deleted == False,
                    CommentDB.moderation_status == "approved"
                )
            ).order_by(CommentDB.created_at).offset(offset).limit(limit).all()
            
            return [self._comment_to_dict(comment) for comment in comments]
        
        return await query_in_executor(
            _get_comments,
            db,
            error_message="Failed to get comments"
        )
    
    async def follow_user(
        self,
        follower_id: str,
        following_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Follow or unfollow a user
        
        Args:
            follower_id: User who is following
            following_id: User being followed
            db: Database session
            
        Returns:
            Updated follow status
        """
        if not db:
            raise DatabaseError("Database session required")
        
        if follower_id == following_id:
            raise ValidationError("Cannot follow yourself")
        
        def _toggle_follow():
            existing_follow = db.query(UserFollowDB).filter(
                and_(
                    UserFollowDB.follower_id == follower_id,
                    UserFollowDB.following_id == following_id
                )
            ).first()
            
            if existing_follow:
                # Unfollow
                db.delete(existing_follow)
                is_following = False
            else:
                # Follow
                follow = UserFollowDB(
                    follower_id=follower_id,
                    following_id=following_id
                )
                db.add(follow)
                is_following = True
            
            db.commit()
            
            return {
                "is_following": is_following
            }
        
        return await query_in_executor(
            _toggle_follow,
            db,
            error_message="Failed to toggle follow"
        )
    
    def _post_to_dict(self, post: PostDB) -> Dict[str, Any]:
        """Convert PostDB to dict"""
        return {
            "post_id": post.post_id,
            "user_id": post.user_id if not post.is_anonymous else None,
            "title": post.title,
            "content": post.content,
            "images": post.images or [],
            "category": post.category,
            "tags": post.tags or [],
            "like_count": post.like_count,
            "comment_count": post.comment_count,
            "view_count": post.view_count,
            "is_anonymous": post.is_anonymous,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "updated_at": post.updated_at.isoformat() if post.updated_at else None
        }
    
    def _comment_to_dict(self, comment: CommentDB) -> Dict[str, Any]:
        """Convert CommentDB to dict"""
        return {
            "comment_id": comment.comment_id,
            "post_id": comment.post_id,
            "user_id": comment.user_id,
            "parent_id": comment.parent_id,
            "content": comment.content,
            "like_count": comment.like_count,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "updated_at": comment.updated_at.isoformat() if comment.updated_at else None
        }

