"""
Community feature database models
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean, Index, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.database import Base


class PostDB(Base):
    """Post table for community feature"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    images = Column(JSON, nullable=True)  # List of image URLs
    category = Column(String, nullable=True, index=True)  # experience, question, mood, advice, etc.
    tags = Column(JSON, nullable=True)  # List of tags
    like_count = Column(Integer, default=0, index=True)
    comment_count = Column(Integer, default=0, index=True)
    view_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False, index=True)
    is_pinned = Column(Boolean, default=False, index=True)
    is_anonymous = Column(Boolean, default=False)  # Anonymous posting option
    moderation_status = Column(String, default="pending")  # pending, approved, rejected, flagged
    moderation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_post_user_created', 'user_id', 'created_at'),
        Index('idx_post_category_created', 'category', 'created_at'),
        Index('idx_post_status_created', 'moderation_status', 'created_at'),
    )


class CommentDB(Base):
    """Comment table for community posts"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String, unique=True, index=True, nullable=False)
    post_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    parent_id = Column(String, nullable=True, index=True)  # For nested replies
    content = Column(Text, nullable=False)
    like_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False, index=True)
    moderation_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes
    __table_args__ = (
        Index('idx_comment_post_created', 'post_id', 'created_at'),
        Index('idx_comment_user_created', 'user_id', 'created_at'),
    )


class PostLikeDB(Base):
    """Post likes table"""
    __tablename__ = "post_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Composite unique index to prevent duplicate likes
    __table_args__ = (
        Index('idx_post_like_unique', 'post_id', 'user_id', unique=True),
    )


class CommentLikeDB(Base):
    """Comment likes table"""
    __tablename__ = "comment_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Composite unique index
    __table_args__ = (
        Index('idx_comment_like_unique', 'comment_id', 'user_id', unique=True),
    )


class PostFavoriteDB(Base):
    """Post favorites/bookmarks table"""
    __tablename__ = "post_favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Composite unique index
    __table_args__ = (
        Index('idx_post_favorite_unique', 'post_id', 'user_id', unique=True),
    )


class UserFollowDB(Base):
    """User follow relationship table"""
    __tablename__ = "user_follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(String, index=True, nullable=False)  # User who follows
    following_id = Column(String, index=True, nullable=False)  # User being followed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Composite unique index
    __table_args__ = (
        Index('idx_user_follow_unique', 'follower_id', 'following_id', unique=True),
        Index('idx_user_following', 'following_id', 'created_at'),
    )


class TopicDB(Base):
    """Topic/category table"""
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # Icon identifier
    post_count = Column(Integer, default=0, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostTopicDB(Base):
    """Post-Topic association table"""
    __tablename__ = "post_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, index=True, nullable=False)
    topic_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite unique index
    __table_args__ = (
        Index('idx_post_topic_unique', 'post_id', 'topic_id', unique=True),
    )


class PostReportDB(Base):
    """Post/comment report table for moderation"""
    __tablename__ = "post_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, unique=True, index=True, nullable=False)
    post_id = Column(String, nullable=True, index=True)  # Nullable if reporting a comment
    comment_id = Column(String, nullable=True, index=True)  # Nullable if reporting a post
    user_id = Column(String, index=True, nullable=False)  # User who reported
    report_type = Column(String, nullable=False)  # spam, inappropriate, harassment, etc.
    reason = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, reviewed, resolved, dismissed
    reviewed_by = Column(String, nullable=True)  # Admin user_id
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
