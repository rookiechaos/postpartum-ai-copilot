"""
Onboarding Service - Manages user onboarding progress
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.database import OnboardingProgressDB
from services.logging_service import logger
from exceptions import DatabaseError, NotFoundError


class OnboardingService:
    """Service for managing onboarding progress"""
    
    def get_progress(
        self,
        user_id: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Get onboarding progress for a user
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            Onboarding progress dictionary or None if not found
        """
        progress = db.query(OnboardingProgressDB).filter(
            OnboardingProgressDB.user_id == user_id
        ).first()
        
        if not progress:
            return None
        
        return self._progress_to_dict(progress)
    
    def create_or_update_progress(
        self,
        user_id: str,
        current_step: int,
        completed_steps: Optional[List[str]] = None,
        personalization_data: Optional[Dict[str, Any]] = None,
        is_completed: bool = False,
        is_skipped: bool = False,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create or update onboarding progress
        
        Args:
            user_id: User ID
            current_step: Current step index
            completed_steps: List of completed step IDs
            personalization_data: Personalization data (baby age, feeding type, etc.)
            is_completed: Whether onboarding is completed
            is_skipped: Whether onboarding was skipped
            db: Database session
        
        Returns:
            Updated onboarding progress dictionary
        """
        try:
            progress = db.query(OnboardingProgressDB).filter(
                OnboardingProgressDB.user_id == user_id
            ).first()
            
            if not progress:
                # Create new progress
                total_steps = 7  # Default total steps
                completion_percentage = (len(completed_steps or []) / total_steps) * 100 if completed_steps else 0.0
                
                progress = OnboardingProgressDB(
                    user_id=user_id,
                    current_step=current_step,
                    completed_steps=completed_steps or [],
                    total_steps=total_steps,
                    completion_percentage=completion_percentage,
                    personalization_data=personalization_data,
                    is_completed=is_completed,
                    is_skipped=is_skipped,
                    started_at=datetime.utcnow()
                )
                db.add(progress)
            else:
                # Update existing progress
                progress.current_step = current_step
                if completed_steps is not None:
                    progress.completed_steps = completed_steps
                if personalization_data is not None:
                    progress.personalization_data = personalization_data
                progress.is_completed = is_completed
                progress.is_skipped = is_skipped
                
                # Calculate completion percentage
                total_steps = progress.total_steps or 7
                completed_count = len(progress.completed_steps or [])
                progress.completion_percentage = (completed_count / total_steps) * 100
                
                if is_completed and not progress.completed_at:
                    progress.completed_at = datetime.utcnow()
            
            db.commit()
            db.refresh(progress)
            
            logger.log_info(
                f"Onboarding progress updated for user {user_id}",
                context={
                    "user_id": user_id,
                    "current_step": current_step,
                    "completion_percentage": progress.completion_percentage,
                    "is_completed": is_completed
                }
            )
            
            return self._progress_to_dict(progress)
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "create_or_update_progress", "user_id": user_id})
            raise DatabaseError(f"Failed to update onboarding progress: {str(e)}")
    
    def mark_step_completed(
        self,
        user_id: str,
        step_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Mark a specific step as completed
        
        Args:
            user_id: User ID
            step_id: Step ID to mark as completed
            db: Database session
        
        Returns:
            Updated onboarding progress dictionary
        """
        progress = db.query(OnboardingProgressDB).filter(
            OnboardingProgressDB.user_id == user_id
        ).first()
        
        if not progress:
            # Create new progress if doesn't exist
            completed_steps = [step_id]
            return self.create_or_update_progress(
                user_id=user_id,
                current_step=0,
                completed_steps=completed_steps,
                db=db
            )
        
        # Add step to completed list if not already there
        completed_steps = progress.completed_steps or []
        if step_id not in completed_steps:
            completed_steps.append(step_id)
        
        # Update completion percentage
        total_steps = progress.total_steps or 7
        completion_percentage = (len(completed_steps) / total_steps) * 100
        
        progress.completed_steps = completed_steps
        progress.completion_percentage = completion_percentage
        progress.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(progress)
        
        return self._progress_to_dict(progress)
    
    def save_personalization_data(
        self,
        user_id: str,
        personalization_data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Save personalization data during onboarding
        
        Args:
            user_id: User ID
            personalization_data: Personalization data (baby age, feeding type, etc.)
            db: Database session
        
        Returns:
            Updated onboarding progress dictionary
        """
        progress = db.query(OnboardingProgressDB).filter(
            OnboardingProgressDB.user_id == user_id
        ).first()
        
        if not progress:
            # Create new progress with personalization data
            return self.create_or_update_progress(
                user_id=user_id,
                current_step=0,
                personalization_data=personalization_data,
                db=db
            )
        
        # Update personalization data
        existing_data = progress.personalization_data or {}
        existing_data.update(personalization_data)
        progress.personalization_data = existing_data
        progress.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(progress)
        
        return self._progress_to_dict(progress)
    
    def _progress_to_dict(self, progress: OnboardingProgressDB) -> Dict[str, Any]:
        """Convert database progress to dictionary"""
        return {
            "user_id": progress.user_id,
            "current_step": progress.current_step,
            "completed_steps": progress.completed_steps or [],
            "total_steps": progress.total_steps,
            "completion_percentage": progress.completion_percentage,
            "is_completed": progress.is_completed,
            "is_skipped": progress.is_skipped,
            "personalization_data": progress.personalization_data or {},
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        }

