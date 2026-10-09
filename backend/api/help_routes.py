"""
Help Routes - API endpoints for help center
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user, get_optional_user
from middleware.admin import require_admin
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger

router = APIRouter()
container = get_container()


class HelpArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str
    language: str = Field(default="en", pattern="^(en|ja|zh)$")
    tags: Optional[List[str]] = None


class FAQCreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1)
    category: Optional[str] = None
    language: str = Field(default="en", pattern="^(en|ja|zh)$")


class HelpFeedback(BaseModel):
    article_id: Optional[str] = None
    faq_id: Optional[str] = None
    is_helpful: bool = True
    comment: Optional[str] = None


@router.get("/articles")
async def get_articles(
    category: Optional[str] = Query(None, description="Filter by category"),
    language: str = Query("en", description="Language code"),
    search: Optional[str] = Query(None, description="Search query"),
    db: Session = Depends(get_db)
):
    """Get help articles with optional filtering"""
    try:
        help_service = container.get("help_service")
        articles = help_service.get_articles(
            category=category,
            language=language,
            search=search,
            db=db
        )
        return {"articles": articles, "total": len(articles)}
    except Exception as e:
        logger.log_error(e, context={"action": "get_articles"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get articles: {str(e)}"
        )


@router.get("/articles/{article_id}")
async def get_article(
    article_id: str,
    db: Session = Depends(get_db)
):
    """Get a single help article"""
    try:
        help_service = container.get("help_service")
        article = help_service.get_article(article_id, db)
        
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        return article
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(e, context={"action": "get_article"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get article: {str(e)}"
        )


@router.get("/faqs")
async def get_faqs(
    category: Optional[str] = Query(None, description="Filter by category"),
    language: str = Query("en", description="Language code"),
    search: Optional[str] = Query(None, description="Search query"),
    db: Session = Depends(get_db)
):
    """Get FAQs with optional filtering"""
    try:
        help_service = container.get("help_service")
        faqs = help_service.get_faqs(
            category=category,
            language=language,
            search=search,
            db=db
        )
        return {"faqs": faqs, "total": len(faqs)}
    except Exception as e:
        logger.log_error(e, context={"action": "get_faqs"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FAQs: {str(e)}"
        )


@router.get("/search")
async def search_help(
    q: str = Query(..., description="Search query"),
    language: str = Query("en", description="Language code"),
    db: Session = Depends(get_db)
):
    """Search help articles and FAQs"""
    try:
        help_service = container.get("help_service")
        results = help_service.search_help(q, language, db)
        return results
    except Exception as e:
        logger.log_error(e, context={"action": "search_help"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search: {str(e)}"
        )


@router.get("/categories")
async def get_categories(
    language: str = Query("en", description="Language code"),
    db: Session = Depends(get_db)
):
    """Get all available categories"""
    try:
        help_service = container.get("help_service")
        categories = help_service.get_categories(language, db)
        return {"categories": categories}
    except Exception as e:
        logger.log_error(e, context={"action": "get_categories"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {str(e)}"
        )


@router.post("/feedback")
async def submit_feedback(
    feedback: HelpFeedback,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Submit feedback for an article or FAQ"""
    try:
        help_service = container.get("help_service")
        user_id = current_user.user_id if current_user else None
        
        result = help_service.submit_feedback(
            article_id=feedback.article_id,
            faq_id=feedback.faq_id,
            user_id=user_id,
            is_helpful=feedback.is_helpful,
            comment=feedback.comment,
            db=db
        )
        
        return result
    except Exception as e:
        logger.log_error(e, context={"action": "submit_feedback"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to submit feedback: {str(e)}"
        )


# Admin endpoints (for creating articles/FAQs)
@router.post("/articles", status_code=status.HTTP_201_CREATED)
async def create_article(
    article: HelpArticleCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new help article (admin only)"""
    try:
        help_service = container.get("help_service")
        created = help_service.create_article(
            title=article.title,
            content=article.content,
            category=article.category,
            language=article.language,
            tags=article.tags,
            db=db
        )
        return created
    except Exception as e:
        logger.log_error(e, context={"action": "create_article"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create article: {str(e)}"
        )


@router.post("/faqs", status_code=status.HTTP_201_CREATED)
async def create_faq(
    faq: FAQCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new FAQ (admin only)"""
    try:
        help_service = container.get("help_service")
        created = help_service.create_faq(
            question=faq.question,
            answer=faq.answer,
            category=faq.category,
            language=faq.language,
            db=db
        )
        return created
    except Exception as e:
        logger.log_error(e, context={"action": "create_faq"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create FAQ: {str(e)}"
        )

