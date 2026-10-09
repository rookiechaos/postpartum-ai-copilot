"""
Feedback Service - Manages user feedback
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models.database import FeedbackDB, NPSSurveyDB, FeatureRequestDB, FeatureVoteDB
from exceptions import DatabaseError, NotFoundError


class FeedbackService:
    """Service for managing user feedback"""
    
    def create_feedback(
        self,
        user_id: str,
        category: str,
        title: str,
        message: str,
        db: Session,
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new feedback entry
        
        Args:
            user_id: User ID
            category: Feedback category (bug, feature, question, other)
            title: Feedback title
            message: Feedback message
            priority: Priority level (low, medium, high)
            metadata: Additional metadata
            db: Database session
        
        Returns:
            Created feedback entry
        """
        try:
            feedback = FeedbackDB(
                user_id=user_id,
                category=category,
                title=title,
                message=message,
                priority=priority,
                status="open",
                extra_metadata=metadata or {}
            )
            db.add(feedback)
            db.commit()
            db.refresh(feedback)
            
            return self._feedback_to_dict(feedback)
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Failed to create feedback: {str(e)}")
    
    def get_feedback(
        self,
        feedback_id: int,
        user_id: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Get feedback by ID
        
        Args:
            feedback_id: Feedback ID
            user_id: User ID (for authorization)
            db: Database session
        
        Returns:
            Feedback entry if found and authorized, None otherwise
        """
        feedback = db.query(FeedbackDB).filter(
            FeedbackDB.id == feedback_id,
            FeedbackDB.user_id == user_id
        ).first()
        
        if not feedback:
            return None
        
        return self._feedback_to_dict(feedback)
    
    def get_user_feedback(
        self,
        user_id: str,
        db: Session,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all feedback for a user
        
        Args:
            user_id: User ID
            db: Database session
            status: Filter by status (optional)
            limit: Maximum number of results
        
        Returns:
            List of feedback entries
        """
        query = db.query(FeedbackDB).filter(FeedbackDB.user_id == user_id)
        
        if status:
            query = query.filter(FeedbackDB.status == status)
        
        feedbacks = query.order_by(desc(FeedbackDB.created_at)).limit(limit).all()
        
        return [self._feedback_to_dict(f) for f in feedbacks]
    
    def update_feedback_status(
        self,
        feedback_id: int,
        user_id: str,
        status: str,
        db: Session,
        response: Optional[str] = None
    ) -> bool:
        """
        Update feedback status
        
        Args:
            feedback_id: Feedback ID
            user_id: User ID (for authorization)
            status: New status
            response: Optional response message
            db: Database session
        
        Returns:
            True if updated successfully
        """
        try:
            feedback = db.query(FeedbackDB).filter(
                FeedbackDB.id == feedback_id,
                FeedbackDB.user_id == user_id
            ).first()
            
            if not feedback:
                return False
            
            feedback.status = status
            if response:
                feedback.response = response
            feedback.updated_at = datetime.utcnow()
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Failed to update feedback: {str(e)}")
    
    def auto_classify_feedback(self, title: str, message: str) -> str:
        """
        Automatically classify feedback category based on content
        
        Args:
            title: Feedback title
            message: Feedback message
        
        Returns:
            Category: bug, feature, question, or other
        """
        text = (title + " " + message).lower()
        
        # Bug keywords
        bug_keywords = ['bug', 'error', 'broken', 'not working', 'crash', 'issue', 'problem', 'fail']
        if any(keyword in text for keyword in bug_keywords):
            return "bug"
        
        # Feature request keywords
        feature_keywords = ['feature', 'add', 'suggest', 'request', 'wish', 'would like', 'could you', 'please add']
        if any(keyword in text for keyword in feature_keywords):
            return "feature"
        
        # Question keywords
        question_keywords = ['how', 'what', 'why', 'when', 'where', '?', 'question', 'help', 'confused']
        if any(keyword in text for keyword in question_keywords):
            return "question"
        
        return "other"
    
    def create_feedback_with_auto_classify(
        self,
        user_id: str,
        title: str,
        message: str,
        db: Session,
        category: Optional[str] = None,
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create feedback with automatic classification
        
        Args:
            user_id: User ID
            title: Feedback title
            message: Feedback message
            db: Database session
            category: Optional category (if not provided, will be auto-classified)
            priority: Priority level
            metadata: Additional metadata
        
        Returns:
            Created feedback entry
        """
        # Auto-classify if category not provided
        if not category:
            category = self.auto_classify_feedback(title, message)
        
        return self.create_feedback(
            user_id=user_id,
            category=category,
            title=title,
            message=message,
            db=db,
            priority=priority,
            metadata=metadata
        )
    
    def submit_nps_survey(
        self,
        user_id: str,
        score: int,
        comment: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Submit NPS survey
        
        Args:
            user_id: User ID
            score: NPS score (0-10)
            comment: Optional comment
            context: Optional context (feature used, page, etc.)
            db: Database session
        
        Returns:
            Created NPS survey entry
        """
        try:
            if not 0 <= score <= 10:
                raise ValueError("NPS score must be between 0 and 10")
            
            survey = NPSSurveyDB(
                user_id=user_id,
                score=score,
                comment=comment,
                context=context or {},
                survey_type="nps"
            )
            db.add(survey)
            db.commit()
            db.refresh(survey)
            
            return {
                "id": survey.id,
                "user_id": survey.user_id,
                "score": survey.score,
                "comment": survey.comment,
                "context": survey.context,
                "created_at": survey.created_at.isoformat() if survey.created_at else None
            }
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Failed to submit NPS survey: {str(e)}")
    
    def get_nps_stats(
        self,
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get NPS statistics
        
        Args:
            days: Number of days to analyze
            db: Database session
        
        Returns:
            NPS statistics
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            surveys = db.query(NPSSurveyDB).filter(
                NPSSurveyDB.created_at >= cutoff_date,
                NPSSurveyDB.survey_type == "nps"
            ).all()
            
            if not surveys:
                return {
                    "total_responses": 0,
                    "promoters": 0,
                    "passives": 0,
                    "detractors": 0,
                    "nps_score": 0,
                    "average_score": 0
                }
            
            promoters = sum(1 for s in surveys if s.score >= 9)
            passives = sum(1 for s in surveys if 7 <= s.score <= 8)
            detractors = sum(1 for s in surveys if s.score <= 6)
            
            total = len(surveys)
            nps_score = ((promoters - detractors) / total) * 100 if total > 0 else 0
            average_score = sum(s.score for s in surveys) / total if total > 0 else 0
            
            return {
                "total_responses": total,
                "promoters": promoters,
                "passives": passives,
                "detractors": detractors,
                "nps_score": round(nps_score, 2),
                "average_score": round(average_score, 2)
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get NPS stats: {str(e)}")
    
    def create_feature_request(
        self,
        feature_name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        created_by: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create or get existing feature request
        
        Args:
            feature_name: Feature name
            description: Feature description
            category: Feature category
            created_by: User ID of creator
            db: Database session
        
        Returns:
            Feature request entry
        """
        try:
            # Check if feature request already exists
            existing = db.query(FeatureRequestDB).filter(
                func.lower(FeatureRequestDB.feature_name) == feature_name.lower()
            ).first()
            
            if existing:
                return {
                    "id": existing.id,
                    "feature_name": existing.feature_name,
                    "description": existing.description,
                    "category": existing.category,
                    "vote_count": existing.vote_count,
                    "status": existing.status,
                    "created_by": existing.created_by,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None
                }
            
            # Create new feature request
            feature_request = FeatureRequestDB(
                feature_name=feature_name,
                description=description,
                category=category,
                created_by=created_by,
                vote_count=0,
                status="open"
            )
            db.add(feature_request)
            db.commit()
            db.refresh(feature_request)
            
            return {
                "id": feature_request.id,
                "feature_name": feature_request.feature_name,
                "description": feature_request.description,
                "category": feature_request.category,
                "vote_count": feature_request.vote_count,
                "status": feature_request.status,
                "created_by": feature_request.created_by,
                "created_at": feature_request.created_at.isoformat() if feature_request.created_at else None
            }
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Failed to create feature request: {str(e)}")
    
    def vote_feature_request(
        self,
        feature_request_id: int,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Vote for a feature request
        
        Args:
            feature_request_id: Feature request ID
            user_id: User ID
            db: Database session
        
        Returns:
            Updated feature request
        """
        try:
            # Check if user already voted
            existing_vote = db.query(FeatureVoteDB).filter(
                FeatureVoteDB.feature_request_id == feature_request_id,
                FeatureVoteDB.user_id == user_id
            ).first()
            
            if existing_vote:
                raise ValueError("User has already voted for this feature")
            
            # Get feature request
            feature_request = db.query(FeatureRequestDB).filter(
                FeatureRequestDB.id == feature_request_id
            ).first()
            
            if not feature_request:
                raise NotFoundError("Feature request not found")
            
            # Create vote
            vote = FeatureVoteDB(
                feature_request_id=feature_request_id,
                user_id=user_id
            )
            db.add(vote)
            
            # Update vote count
            feature_request.vote_count += 1
            feature_request.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(feature_request)
            
            return {
                "id": feature_request.id,
                "feature_name": feature_request.feature_name,
                "description": feature_request.description,
                "category": feature_request.category,
                "vote_count": feature_request.vote_count,
                "status": feature_request.status,
                "created_by": feature_request.created_by,
                "created_at": feature_request.created_at.isoformat() if feature_request.created_at else None
            }
        except Exception as e:
            db.rollback()
            if isinstance(e, (NotFoundError, ValueError)):
                raise
            raise DatabaseError(f"Failed to vote for feature request: {str(e)}")
    
    def get_feature_requests(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Get feature requests
        
        Args:
            status: Filter by status
            category: Filter by category
            limit: Maximum number of results
            db: Database session
        
        Returns:
            List of feature requests
        """
        query = db.query(FeatureRequestDB)
        
        if status:
            query = query.filter(FeatureRequestDB.status == status)
        if category:
            query = query.filter(FeatureRequestDB.category == category)
        
        feature_requests = query.order_by(
            desc(FeatureRequestDB.vote_count),
            desc(FeatureRequestDB.created_at)
        ).limit(limit).all()
        
        return [{
            "id": fr.id,
            "feature_name": fr.feature_name,
            "description": fr.description,
            "category": fr.category,
            "vote_count": fr.vote_count,
            "status": fr.status,
            "created_by": fr.created_by,
            "created_at": fr.created_at.isoformat() if fr.created_at else None
        } for fr in feature_requests]
    
    def _feedback_to_dict(self, feedback: FeedbackDB) -> Dict[str, Any]:
        """Convert database feedback to dictionary"""
        return {
            "id": feedback.id,
            "user_id": feedback.user_id,
            "category": feedback.category,
            "title": feedback.title,
            "message": feedback.message,
            "priority": feedback.priority,
            "status": feedback.status,
            "response": feedback.response,
            "metadata": feedback.extra_metadata or {},
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
            "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None
        }

