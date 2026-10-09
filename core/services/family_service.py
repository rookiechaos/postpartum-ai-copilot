"""
Family Service - Family sharing and multi-user support
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid
import json
import asyncio
from models.database import FamilyDB, FamilyMemberDB, TrackingEntryDB, TaskDB
from services.logging_service import logger
from exceptions import NotFoundError, ValidationError

if TYPE_CHECKING:
    from services.tracking_service import TrackingService
    from services.ai_service import AIService


class FamilyService:
    """Service for managing family groups and sharing"""

    @staticmethod
    def _shares_tracking(member: FamilyMemberDB) -> bool:
        return (member.permissions or {}).get("share_tracking") is True
    
    def create_family(
        self,
        user_id: str,
        name: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Create a new family group
        
        Args:
            user_id: User ID of creator
            name: Family name
            db: Database session
        
        Returns:
            Created family dictionary
        """
        try:
            family_id = f"family_{uuid.uuid4().hex[:12]}"
            
            family = FamilyDB(
                family_id=family_id,
                name=name,
                created_by=user_id
            )
            db.add(family)
            
            # Add creator as owner
            member = FamilyMemberDB(
                family_id=family_id,
                user_id=user_id,
                role="owner",
                status="active",
                permissions={"share_tracking": False},
                joined_at=datetime.utcnow()
            )
            db.add(member)
            
            db.commit()
            db.refresh(family)
            
            logger.log_info(f"Family created: {family_id} by user {user_id}")
            
            return self._family_to_dict(family)
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "create_family", "user_id": user_id})
            raise
    
    def invite_member(
        self,
        family_id: str,
        inviter_user_id: str,
        invitee_user_id: str,
        role: str = "member",
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Invite a user to join a family
        
        Args:
            family_id: Family ID
            inviter_user_id: User ID of inviter
            invitee_user_id: User ID to invite
            role: Role to assign (owner, admin, member, viewer)
            db: Database session
        
        Returns:
            Created member invitation
        """
        try:
            # Check if inviter has permission
            inviter_member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == inviter_user_id,
                    FamilyMemberDB.status == "active"
                )
            ).first()
            
            if not inviter_member or inviter_member.role not in ["owner", "admin"]:
                raise ValidationError("Only owners and admins can invite members")
            
            # Check if already a member
            existing = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == invitee_user_id
                )
            ).first()
            
            if existing:
                if existing.status == "active":
                    raise ValidationError("User is already a member")
                # Reactivate if previously inactive
                existing.status = "pending"
                existing.invited_by = inviter_user_id
                existing.role = role
            else:
                # Create new invitation
                member = FamilyMemberDB(
                    family_id=family_id,
                    user_id=invitee_user_id,
                    role=role,
                    invited_by=inviter_user_id,
                    status="pending"
                )
                db.add(member)
            
            db.commit()
            
            logger.log_info(
                f"Member invited: {invitee_user_id} to family {family_id} by {inviter_user_id}"
            )
            
            return {"status": "invited", "family_id": family_id, "user_id": invitee_user_id}
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "invite_member", "family_id": family_id})
            raise
    
    def accept_invitation(
        self,
        family_id: str,
        user_id: str,
        db: Session
    ) -> bool:
        """Accept a family invitation"""
        try:
            member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == user_id,
                    FamilyMemberDB.status == "pending"
                )
            ).first()
            
            if not member:
                raise NotFoundError("Invitation not found")
            
            member.status = "active"
            member.joined_at = datetime.utcnow()
            db.commit()
            
            logger.log_info(f"User {user_id} accepted invitation to family {family_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "accept_invitation", "family_id": family_id})
            raise
    
    def get_user_families(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get all families a user belongs to"""
        try:
            members = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.user_id == user_id,
                    FamilyMemberDB.status == "active"
                )
            ).all()
            
            family_ids = [m.family_id for m in members]
            if not family_ids:
                return []
            
            families = db.query(FamilyDB).filter(
                FamilyDB.family_id.in_(family_ids)
            ).all()
            
            return [self._family_to_dict(f) for f in families]
        except Exception as e:
            logger.log_error(e, context={"action": "get_user_families", "user_id": user_id})
            return []
    
    def get_family_members(
        self,
        family_id: str,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get all members of a family (user must be a member)"""
        try:
            # Check if user is a member
            user_member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == user_id,
                    FamilyMemberDB.status == "active"
                )
            ).first()
            
            if not user_member:
                raise ValidationError("You are not a member of this family")
            
            members = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.status == "active"
                )
            ).all()
            
            return [self._member_to_dict(m) for m in members]
        except Exception as e:
            logger.log_error(e, context={"action": "get_family_members", "family_id": family_id})
            raise
    
    def get_shared_tracking_data(
        self,
        family_id: str,
        user_id: str,
        days: int = 7,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Get shared tracking data from all family members"""
        try:
            # Check if user is a member
            user_member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == user_id,
                    FamilyMemberDB.status == "active"
                )
            ).first()
            
            if not user_member:
                raise ValidationError("You are not a member of this family")
            
            # Get all active members
            members = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.status == "active"
                )
            ).all()
            
            member_user_ids = [m.user_id for m in members if self._shares_tracking(m)]
            if not member_user_ids:
                return []
            
            # Get tracking entries from all members
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            entries = db.query(TrackingEntryDB).filter(
                and_(
                    TrackingEntryDB.user_id.in_(member_user_ids),
                    TrackingEntryDB.timestamp >= cutoff_date
                )
            ).order_by(TrackingEntryDB.timestamp.desc()).all()
            
            # Convert to dict format
            result = []
            for entry in entries:
                result.append({
                    "id": entry.id,
                    "user_id": entry.user_id,
                    "entry_type": entry.entry_type,
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                    "feeding_type": entry.feeding_type,
                    "duration_minutes": entry.duration_minutes,
                    "amount_ml": entry.amount_ml,
                    "diaper_type": entry.diaper_type,
                    "sleep_duration_minutes": entry.sleep_duration_minutes,
                    "mood_level": entry.mood_level,
                    "notes": entry.notes
                })
            
            return result
        except Exception as e:
            logger.log_error(e, context={"action": "get_shared_tracking_data", "family_id": family_id})
            raise
    
    def remove_member(
        self,
        family_id: str,
        member_user_id: str,
        remover_user_id: str,
        db: Session
    ) -> bool:
        """Remove a member from family (only owner/admin can remove)"""
        try:
            # Check if remover has permission
            remover_member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == remover_user_id,
                    FamilyMemberDB.status == "active"
                )
            ).first()
            
            if not remover_member or remover_member.role not in ["owner", "admin"]:
                raise ValidationError("Only owners and admins can remove members")
            
            # Cannot remove owner
            member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == member_user_id
                )
            ).first()
            
            if member and member.role == "owner":
                raise ValidationError("Cannot remove the owner")
            
            if member:
                member.status = "inactive"
                db.commit()
                logger.log_info(f"Member {member_user_id} removed from family {family_id}")
                return True
            
            return False
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "remove_member", "family_id": family_id})
            raise
    
    def _family_to_dict(self, family: FamilyDB) -> Dict[str, Any]:
        """Convert database family to dictionary"""
        return {
            "family_id": family.family_id,
            "name": family.name,
            "created_by": family.created_by,
            "created_at": family.created_at.isoformat() if family.created_at else None,
            "updated_at": family.updated_at.isoformat() if family.updated_at else None
        }
    
    def _member_to_dict(self, member: FamilyMemberDB) -> Dict[str, Any]:
        """Convert database member to dictionary"""
        return {
            "id": member.id,
            "family_id": member.family_id,
            "user_id": member.user_id,
            "role": member.role,
            "status": member.status,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "permissions": member.permissions or {}
        }
    
    async def generate_family_summary(
        self,
        family_id: str,
        user_id: str,
        period: str = "daily",  # "daily" or "weekly"
        tracking_service: Optional["TrackingService"] = None,
        ai_service: Optional["AIService"] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Generate family summary for partner viewing
        
        Args:
            family_id: Family ID
            user_id: User ID requesting summary
            period: "daily" or "weekly"
            tracking_service: TrackingService instance
            ai_service: AIService instance
            db: Database session
        
        Returns:
            Family summary with tracking data and AI insights
        """
        try:
            # Check if user is a member
            user_member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == user_id,
                    FamilyMemberDB.status == "active"
                )
            ).first()
            
            if not user_member:
                raise ValidationError("You are not a member of this family")
            
            # Get all active members (excluding the requester if they want to see others' data)
            members = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.status == "active"
                )
            ).all()
            
            # Get shared tracking data
            shared_data = self.get_shared_tracking_data(family_id, user_id, days=7 if period == "daily" else 30, db=db)
            
            # Summaries must enforce the same sharing policy as the raw records.
            shared_members = [member for member in members if self._shares_tracking(member)]
            shared_members.sort(key=lambda member: (member.role != "owner", member.id))
            primary_user_id = shared_members[0].user_id if shared_members else None
            
            summary = {}
            if primary_user_id and tracking_service and ai_service:
                if period == "daily":
                    summary = await tracking_service.generate_daily_summary(
                        user_id=primary_user_id,
                        db=db,
                        ai_service=ai_service
                    )
                else:
                    summary = await tracking_service.generate_weekly_summary(
                        user_id=primary_user_id,
                        db=db,
                        ai_service=ai_service
                    )
            
            return {
                "family_id": family_id,
                "period": period,
                "summary": summary,
                "shared_entries_count": len(shared_data),
                "members_count": len(members),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.log_error(e, context={"action": "generate_family_summary", "family_id": family_id})
            raise
    
    def share_tracking_data(
        self,
        family_id: str,
        user_id: str,
        share_enabled: bool = True,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Enable/disable sharing of tracking data with family
        
        Args:
            family_id: Family ID
            user_id: User ID
            share_enabled: Whether to enable sharing
            db: Database session
        
        Returns:
            Updated sharing status
        """
        try:
            # Check if user is a member
            member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == user_id,
                    FamilyMemberDB.status == "active"
                )
            ).first()
            
            if not member:
                raise ValidationError("You are not a member of this family")
            
            # Update permissions
            member.permissions = {**(member.permissions or {}), "share_tracking": share_enabled}
            db.commit()
            db.refresh(member)
            
            return {
                "family_id": family_id,
                "user_id": user_id,
                "share_enabled": share_enabled,
                "message": "Sharing preference updated"
            }
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "share_tracking_data", "family_id": family_id})
            raise
    
    def create_family_task(
        self,
        family_id: str,
        creator_user_id: str,
        title: str,
        description: Optional[str] = None,
        assigned_to_user_id: Optional[str] = None,
        priority: str = "medium",
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Create a family task for coordination
        
        Args:
            family_id: Family ID
            creator_user_id: User ID creating the task
            title: Task title
            description: Task description
            assigned_to_user_id: User ID to assign task to (optional)
            priority: Task priority (high, medium, low)
            db: Database session
        
        Returns:
            Created task dictionary
        """
        try:
            # Check if creator is a member
            creator_member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == creator_user_id,
                    FamilyMemberDB.status == "active"
                )
            ).first()
            
            if not creator_member:
                raise ValidationError("You are not a member of this family")
            
            # Create task
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            task = TaskDB(
                task_id=task_id,
                task_type="family_task",
                task_data=json.dumps({
                    "family_id": family_id,
                    "title": title,
                    "description": description,
                    "creator_user_id": creator_user_id,
                    "assigned_to_user_id": assigned_to_user_id,
                    "priority": priority
                }),
                user_id=creator_user_id,
                status="pending",
                priority=priority
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            
            logger.log_info(f"Family task created: {task_id} in family {family_id}")
            
            return {
                "task_id": task_id,
                "family_id": family_id,
                "title": title,
                "description": description,
                "status": "pending",
                "priority": priority,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "create_family_task", "family_id": family_id})
            raise
