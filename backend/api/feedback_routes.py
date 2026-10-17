"""
Feedback API Routes - User feedback collection and management
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.auth import get_current_user, get_optional_user
from middleware.admin import require_admin
from models.schemas import User
from services.logging_service import logger
from dependencies.container import get_container
from exceptions import NotFoundError, DatabaseError, ValidationError

router = APIRouter(prefix="/api/feedback", tags=["feedback"])
container = get_container()


class FeedbackCreate(BaseModel):
    """Feedback creation model"""
    category: str = Field(..., description="Feedback category: bug, feature, question, other", max_length=50)
    title: str = Field(..., description="Feedback title", min_length=1, max_length=200)
    message: str = Field(..., description="Feedback message", min_length=1, max_length=5000)
    priority: Optional[str] = Field(default="medium", description="Priority: low, medium, high", max_length=20)
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")
    
    @validator('category')
    def validate_category(cls, v):
        """Validate feedback category"""
        allowed = ["bug", "feature", "question", "other"]
        if v.lower() not in allowed:
            from exceptions import ValidationError
            raise ValidationError(f"Category must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate priority"""
        if v and v.lower() not in ["low", "medium", "high"]:
            from exceptions import ValidationError
            raise ValidationError("Priority must be one of: low, medium, high")
        return v.lower() if v else "medium"


class FeedbackResponse(BaseModel):
    """Feedback response model"""
    id: int
    user_id: str
    category: str
    title: str
    message: str
    priority: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    response: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create user feedback
    
    Categories:
    - bug: Bug report
    - feature: Feature request
    - question: Question or support request
    - other: Other feedback
    """
    try:
        feedback_service = container.get("feedback_service")
        feedback_entry = feedback_service.create_feedback(
            user_id=current_user.user_id,
            category=feedback.category,
            title=feedback.title,
            message=feedback.message,
            db=db,
            priority=feedback.priority,
            metadata=feedback.metadata
        )
        
        # Log feedback creation
        logger.log_user_action(
            user_id=current_user.user_id,
            action="feedback_created",
            details={
                "feedback_id": feedback_entry["id"],
                "category": feedback.category,
                "priority": feedback.priority
            }
        )
        
        return FeedbackResponse(**feedback_entry)
    except DatabaseError as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail=f"Failed to create feedback: {str(e)}")


@router.get("", response_model=List[FeedbackResponse])
async def get_user_feedback(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get feedback for current user
    
    Args:
        status: Filter by status (open, in_progress, resolved, closed)
    """
    try:
        feedback_service = container.get("feedback_service")
        feedbacks = feedback_service.get_user_feedback(
            user_id=current_user.user_id,
            db=db,
            status=status
        )
        
        return [FeedbackResponse(**f) for f in feedbacks]
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get feedback: {str(e)}")


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific feedback by ID"""
    try:
        feedback_service = container.get("feedback_service")
        feedback = feedback_service.get_feedback(
            feedback_id=feedback_id,
            user_id=current_user.user_id,
            db=db
        )
        
        if not feedback:
            raise NotFoundError("Feedback not found")
        
        return FeedbackResponse(**feedback)
    except NotFoundError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get feedback: {str(e)}")


# NPS Survey endpoints
class NPSSurveyRequest(BaseModel):
    """NPS Survey request model"""
    score: int = Field(..., ge=0, le=10, description="NPS score (0-10)")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")
    context: Optional[dict] = Field(None, description="Additional context")


@router.post("/nps", status_code=status.HTTP_201_CREATED)
async def submit_nps_survey(
    survey: NPSSurveyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit NPS (Net Promoter Score) survey"""
    try:
        feedback_service = container.get("feedback_service")
        result = feedback_service.submit_nps_survey(
            user_id=current_user.user_id,
            score=survey.score,
            comment=survey.comment,
            context=survey.context,
            db=db
        )
        
        logger.log_user_action(
            user_id=current_user.user_id,
            action="nps_survey_submitted",
            details={"score": survey.score}
        )
        
        return {"status": "success", "survey": result}
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to submit NPS survey: {str(e)}")


@router.get("/nps/stats")
async def get_nps_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get operator-only NPS statistics"""
    try:
        feedback_service = container.get("feedback_service")
        stats = feedback_service.get_nps_stats(days=days, db=db)
        return stats
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e)
        raise DatabaseError(f"Failed to get NPS stats: {str(e)}")


# Feature Request endpoints
class FeatureRequestCreate(BaseModel):
    """Feature request creation model"""
    feature_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=50)


@router.post("/features", status_code=status.HTTP_201_CREATED)
async def create_feature_request(
    request: FeatureRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or get existing feature request"""
    try:
        feedback_service = container.get("feedback_service")
        feature = feedback_service.create_feature_request(
            feature_name=request.feature_name,
            description=request.description,
            category=request.category,
            created_by=current_user.user_id,
            db=db
        )
        
        return {"status": "success", "feature": feature}
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to create feature request: {str(e)}")


@router.post("/features/{feature_request_id}/vote", status_code=status.HTTP_200_OK)
async def vote_feature_request(
    feature_request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vote for a feature request"""
    try:
        feedback_service = container.get("feedback_service")
        feature = feedback_service.vote_feature_request(
            feature_request_id=feature_request_id,
            user_id=current_user.user_id,
            db=db
        )
        
        logger.log_user_action(
            user_id=current_user.user_id,
            action="feature_voted",
            details={"feature_request_id": feature_request_id}
        )
        
        return {"status": "success", "feature": feature}
    except (DatabaseError, NotFoundError, ValueError):
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to vote for feature request: {str(e)}")


@router.get("/features", status_code=status.HTTP_200_OK)
async def get_feature_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get feature requests"""
    try:
        feedback_service = container.get("feedback_service")
        features = feedback_service.get_feature_requests(
            status=status,
            category=category,
            limit=limit,
            db=db
        )
        
        return {"features": features, "total": len(features)}
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e)
        raise DatabaseError(f"Failed to get feature requests: {str(e)}")


# Auto-classify feedback endpoint
@router.post("/auto-classify", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback_auto_classify(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create feedback with automatic classification"""
    try:
        feedback_service = container.get("feedback_service")
        feedback_entry = feedback_service.create_feedback_with_auto_classify(
            user_id=current_user.user_id,
            title=feedback.title,
            message=feedback.message,
            db=db,
            category=feedback.category,  # Optional, will be auto-classified if not provided
            priority=feedback.priority,
            metadata=feedback.metadata
        )
        
        logger.log_user_action(
            user_id=current_user.user_id,
            action="feedback_created_auto_classified",
            details={
                "feedback_id": feedback_entry["id"],
                "category": feedback_entry["category"]
            }
        )
        
        return FeedbackResponse(**feedback_entry)
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to create feedback: {str(e)}")

