"""
Community API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.auth import get_optional_user, get_current_user
from models.schemas import User
from exceptions import DatabaseError, ValidationError, NotFoundError
from dependencies.container import get_container

router = APIRouter()

# Get service instance from container
container = get_container()


@router.post("/api/community/posts")
async def create_post(
    title: str,
    content: str,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    images: Optional[List[str]] = None,
    is_anonymous: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new post"""
    community_service = container.get("community_service")
    try:
        post = await community_service.create_post(
            user_id=current_user.user_id,
            title=title,
            content=content,
            category=category,
            tags=tags,
            images=images,
            is_anonymous=is_anonymous,
            db=db
        )
        return {"success": True, "post": post}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/community/posts")
async def get_posts(
    user_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    topic_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get posts list"""
    community_service = container.get("community_service")
    try:
        posts = await community_service.get_posts(
            user_id=user_id,
            category=category,
            topic_id=topic_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            db=db
        )
        return {"success": True, "posts": posts, "count": len(posts)}
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/community/posts/mine")
async def get_my_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    posts = await container.get("community_service").get_posts(
        user_id=current_user.user_id, db=db, include_anonymous=True,
    )
    return {"success": True, "posts": posts, "count": len(posts)}


@router.get("/api/community/posts/{post_id}")
async def get_post(
    post_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get a single post"""
    community_service = container.get("community_service")
    try:
        user_id = current_user.user_id if current_user else None
        post = await community_service.get_post(
            post_id=post_id,
            user_id=user_id,
            db=db
        )
        return {"success": True, "post": post}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/community/posts/{post_id}/like")
async def like_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Like or unlike a post"""
    community_service = container.get("community_service")
    try:
        result = await community_service.like_post(
            post_id=post_id,
            user_id=current_user.user_id,
            db=db
        )
        return {"success": True, **result}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/community/posts/{post_id}/favorite")
async def favorite_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Favorite or unfavorite a post"""
    community_service = container.get("community_service")
    try:
        result = await community_service.favorite_post(
            post_id=post_id,
            user_id=current_user.user_id,
            db=db
        )
        return {"success": True, **result}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/community/posts/{post_id}/comments")
async def create_comment(
    post_id: str,
    content: str,
    parent_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a comment on a post"""
    community_service = container.get("community_service")
    try:
        comment = await community_service.create_comment(
            post_id=post_id,
            user_id=current_user.user_id,
            content=content,
            parent_id=parent_id,
            db=db
        )
        return {"success": True, "comment": comment}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/community/posts/{post_id}/comments")
async def get_comments(
    post_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get comments for a post"""
    community_service = container.get("community_service")
    try:
        comments = await community_service.get_comments(
            post_id=post_id,
            limit=limit,
            offset=offset,
            db=db
        )
        return {"success": True, "comments": comments, "count": len(comments)}
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/community/users/{user_id}/follow")
async def follow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Follow or unfollow a user"""
    community_service = container.get("community_service")
    try:
        result = await community_service.follow_user(
            follower_id=current_user.user_id,
            following_id=user_id,
            db=db
        )
        return {"success": True, **result}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

