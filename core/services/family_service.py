"""
Family Service - Family sharing and multi-user support
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid
import json
import asyncio
from models.database import FamilyDB, FamilyMemberDB, TrackingEntryDB, TaskDB, UserDB, CareSubjectDB
from sqlalchemy.exc import IntegrityError
from services.logging_service import logger
from exceptions import NotFoundError, ValidationError, ConflictError
from services.ai_data_scope import CARE_TYPES, PARENT_TYPES, records_for_ai

FAMILY_SHARED_DAYS = 7
ID_INVITATION_VERSION = 1


def lock_family_membership_changes(db: Session, family_id: str) -> FamilyDB:
    """Serialize family invitation transitions on PostgreSQL and SQLite.

    A no-op write works where FOR UPDATE is ignored. Call this before reading
    memberships so acceptance cannot race an issuer's removal or re-invitation.
    Link writers share this lock before touching membership or invitation rows.
    Updating updated_at to itself avoids changing a family's display timestamp.
    """
    changed = db.query(FamilyDB).filter(FamilyDB.family_id == family_id).update(
        {"updated_at": FamilyDB.updated_at}, synchronize_session=False
    )
    if changed != 1:
        raise NotFoundError("Family not found")
    return db.query(FamilyDB).populate_existing().filter(FamilyDB.family_id == family_id).one()

if TYPE_CHECKING:
    from services.tracking_service import TrackingService
    from services.ai_service import AIService


class FamilyService:
    """Service for managing family groups and sharing"""

    @staticmethod
    def _shares_tracking(member: FamilyMemberDB) -> bool:
        permissions = member.permissions or {}
        return permissions.get("share_baby") is True or permissions.get("share_parent") is True

    @staticmethod
    def _lock_members_in_order(db: Session, family_id: str, user_ids) -> Dict[str, FamilyMemberDB]:
        """Use the same user-ID lock order as handover acknowledgements.

        Pending and inactive recipients also need locks: invitation acceptance,
        decline and rejoining can change their rows while an issuer is checked.
        The family lock must already be held before calling this helper.
        """
        members = {}
        for user_id in sorted({value for value in user_ids if value is not None}):
            member = db.query(FamilyMemberDB).populate_existing().filter(
                FamilyMemberDB.family_id == family_id, FamilyMemberDB.user_id == user_id,
            ).first()
            if member is None:
                continue
            changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == member.id,
                FamilyMemberDB.status == member.status, FamilyMemberDB.revision == member.revision,
                FamilyMemberDB.role == member.role,
            ).update({"revision": member.revision, "updated_at": FamilyMemberDB.updated_at},
                synchronize_session=False)
            if changed != 1:
                raise ConflictError("Membership changed; review the invitation again")
            members[user_id] = member
        return members

    @staticmethod
    def _issued_pending_user_ids(db: Session, family_id: str, inviter_user_id: str) -> List[str]:
        return [user_id for user_id, in db.query(FamilyMemberDB.user_id).filter(
            FamilyMemberDB.family_id == family_id, FamilyMemberDB.invited_by == inviter_user_id,
            FamilyMemberDB.status == "pending").all()]

    @staticmethod
    def _current_id_invitation(member: FamilyMemberDB, family: FamilyDB,
                               inviter: Optional[FamilyMemberDB]) -> bool:
        permissions = member.permissions if isinstance(member.permissions, dict) else {}
        invitation = permissions.get("_id_invitation")
        if not isinstance(invitation, dict) or type(invitation.get("version")) is not int:
            return False
        revision = invitation.get("inviter_revision")
        if invitation["version"] != ID_INVITATION_VERSION or type(revision) is not int or revision < 1:
            return False
        is_creator = inviter is not None and family.created_by == inviter.user_id
        return bool(member.status == "pending" and member.role in {"admin", "member", "viewer"}
            and inviter is not None and inviter.family_id == family.family_id
            and member.invited_by == inviter.user_id and inviter.status == "active"
            and inviter.revision == revision and (is_creator or inviter.role == "admin")
            and (member.role != "admin" or is_creator))

    @staticmethod
    def _revoke_issued_id_invitations(db: Session, family_id: str, inviter_user_id: str) -> None:
        # Callers already hold the family lock and every current pending
        # recipient row in user-ID order; no ID invitation can add a new row here.
        db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family_id,
            FamilyMemberDB.invited_by == inviter_user_id, FamilyMemberDB.status == "pending",
        ).update({"status": "inactive", "permissions": {},
            "revision": FamilyMemberDB.revision + 1}, synchronize_session=False)

    def get_pending_invitations(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        rows = db.query(FamilyMemberDB, FamilyDB).join(FamilyDB,
            FamilyMemberDB.family_id == FamilyDB.family_id).filter(
            FamilyMemberDB.user_id == user_id, FamilyMemberDB.status == "pending").all()
        result = []
        for member, family in rows:
            inviter = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family.family_id,
                FamilyMemberDB.user_id == member.invited_by).first()
            # Old pending rows have no trustworthy issuer version. Hide them and
            # reject acceptance until a current manager explicitly re-invites.
            if self._current_id_invitation(member, family, inviter):
                result.append({"family_id": family.family_id, "name": family.name})
        return result
    
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
            role: Role to assign (admin, member, viewer)
            db: Database session
        
        Returns:
            Created member invitation
        """
        try:
            family = lock_family_membership_changes(db, family_id)
            if role not in {"admin", "member", "viewer"}:
                raise ValidationError("Invitations cannot grant ownership")
            # Check if inviter has permission
            members = self._lock_members_in_order(db, family_id, (inviter_user_id, invitee_user_id))
            inviter_member = members.get(inviter_user_id)
            
            is_creator = family.created_by == inviter_user_id
            if not inviter_member or inviter_member.status != "active" or (not is_creator and inviter_member.role != "admin"):
                raise ValidationError("Only owners and admins can invite members")
            if role == "admin" and not is_creator:
                raise ValidationError("Only the family creator can invite admins")
            if not db.query(UserDB).filter(UserDB.user_id == invitee_user_id, UserDB.is_active.is_(True)).first():
                raise ValidationError("Cannot invite this account")
            invitation_permissions = {"_id_invitation": {"version": ID_INVITATION_VERSION,
                "inviter_revision": inviter_member.revision}}
            
            # Check if already a member
            existing = members.get(invitee_user_id)
            
            if existing:
                if existing.status == "active":
                    raise ValidationError("User is already a member")
                # Keep the version monotonic across invitations and re-joining.
                changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == existing.id,
                    FamilyMemberDB.status == existing.status, FamilyMemberDB.revision == existing.revision,
                ).update({"status": "pending", "invited_by": inviter_user_id, "role": role,
                    "permissions": invitation_permissions, "revision": existing.revision + 1}, synchronize_session=False)
                if changed != 1:
                    raise ConflictError("Membership changed; refresh before inviting again")
            else:
                # Create new invitation
                member = FamilyMemberDB(
                    family_id=family_id,
                    user_id=invitee_user_id,
                    role=role,
                    invited_by=inviter_user_id,
                    status="pending",
                    permissions=invitation_permissions,
                )
                db.add(member)
            
            db.commit()
            
            logger.log_info(
                f"Member invited: {invitee_user_id} to family {family_id} by {inviter_user_id}"
            )
            
            return {"status": "invited", "family_id": family_id, "user_id": invitee_user_id}
        except IntegrityError:
            db.rollback()
            raise ConflictError("Membership changed; refresh before inviting again") from None
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
            family = lock_family_membership_changes(db, family_id)
            member = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.user_id == user_id,
                    FamilyMemberDB.status == "pending"
                )
            ).first()
            
            if not member:
                raise NotFoundError("Invitation not found")
            expected_revision, inviter_id = member.revision, member.invited_by
            members = self._lock_members_in_order(db, family_id, (user_id, inviter_id))
            member, inviter = members.get(user_id), members.get(inviter_id)
            # Re-read both rows under the shared ordering before trusting the
            # issuer or the recipient's pending invitation snapshot.
            if (member is None or member.revision != expected_revision or member.invited_by != inviter_id
                or not self._current_id_invitation(member, family, inviter)):
                raise NotFoundError("Invitation is no longer available; request a new invitation")
            
            changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == member.id,
                FamilyMemberDB.status == "pending", FamilyMemberDB.revision == member.revision,
            ).update({"status": "active", "permissions": {}, "joined_at": datetime.utcnow(),
                "revision": member.revision + 1}, synchronize_session=False)
            if changed != 1:
                raise NotFoundError("Invitation is no longer available")
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
            raise
    
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
                    FamilyMemberDB.status.in_(["active", "pending"] if user_member.role in {"owner", "admin"} else ["active"])
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
            if not 1 <= days <= FAMILY_SHARED_DAYS:
                raise ValidationError("Family sharing is limited to the last 7 days")
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
                    or_(TrackingEntryDB.timestamp >= cutoff_date, TrackingEntryDB.end_timestamp >= cutoff_date)
                )
            ).order_by(TrackingEntryDB.timestamp.desc()).all()
            
            preferences = {member.user_id: member.permissions or {} for member in members}
            subject = db.query(CareSubjectDB).filter(CareSubjectDB.family_id == family_id).first()
            result = []
            for entry in entries:
                scope = preferences[entry.user_id]
                allowed = (CARE_TYPES if scope.get("share_baby") is True else set()) | (
                    PARENT_TYPES if scope.get("share_parent") is True else set())
                if entry.entry_type not in allowed:
                    continue
                if entry.entry_type in CARE_TYPES and (subject is None or entry.subject_id != subject.subject_id or not entry.family_shared):
                    continue
                raw = {column.name: getattr(entry, column.name) for column in TrackingEntryDB.__table__.columns}
                raw["timestamp"] = entry.timestamp.isoformat() if entry.timestamp else None
                selected = records_for_ai([raw], scope.get("share_parent"), scope.get("share_notes"))[0]
                result.append({**selected, "record_key": entry.record_key, "revision": entry.revision, "recorded_by": entry.user_id,
                    "subject_id": entry.subject_id if entry.entry_type in CARE_TYPES else None,
                    "subject_name": subject.nickname if subject and entry.entry_type in CARE_TYPES else None,
                    "end_timestamp": entry.end_timestamp.isoformat() if entry.end_timestamp else None,
                    "recorder_label": scope.get("display_label", "")})
            
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
            family = lock_family_membership_changes(db, family_id)
            # Check if remover has permission
            pending_user_ids = self._issued_pending_user_ids(db, family_id, member_user_id)
            members = self._lock_members_in_order(db, family_id,
                [remover_user_id, member_user_id, *pending_user_ids])
            remover_member = members.get(remover_user_id)
            
            is_creator = family.created_by == remover_user_id
            if not remover_member or remover_member.status != "active" or (not is_creator and remover_member.role != "admin"):
                raise ValidationError("Only owners and admins can remove members")
            
            # Cannot remove owner
            member = members.get(member_user_id)
            
            if member_user_id == family.created_by:
                raise ValidationError("Cannot remove the family creator")
            if member and member.role in {"owner", "admin"} and not is_creator:
                raise ValidationError("Only the family creator can remove admins or legacy owners")
            
            if member:
                changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == member.id,
                    FamilyMemberDB.revision == member.revision,
                ).update({"status": "inactive", "permissions": {},
                    "revision": member.revision + 1}, synchronize_session=False)
                if changed != 1:
                    raise ConflictError("Membership changed; refresh before revoking again")
                self._revoke_issued_id_invitations(db, family_id, member_user_id)
                db.commit()
                logger.log_info(f"Member {member_user_id} removed from family {family_id}")
                return True
            
            return False
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "remove_member", "family_id": family_id})
            raise

    def leave_family(self, family_id: str, user_id: str, db: Session) -> bool:
        try:
            family = lock_family_membership_changes(db, family_id)
            if family.created_by == user_id:
                raise ValidationError("The creator must revoke other memberships instead of leaving")
            pending_user_ids = self._issued_pending_user_ids(db, family_id, user_id)
            members = self._lock_members_in_order(db, family_id, [user_id, *pending_user_ids])
            member = members.get(user_id)
            if member is None or member.status != "active":
                raise NotFoundError("Membership not found")
            changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == member.id,
                FamilyMemberDB.revision == member.revision, FamilyMemberDB.status == "active",
            ).update({"status": "inactive", "permissions": {},
                "revision": FamilyMemberDB.revision + 1}, synchronize_session=False)
            if changed != 1:
                raise NotFoundError("Membership not found")
            self._revoke_issued_id_invitations(db, family_id, user_id)
            db.commit()
            return True
        except Exception:
            db.rollback()
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
            "revision": member.revision,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "permissions": {} if member.status == "pending" else member.permissions or {}
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
        """Count consented records by Japan calendar day without external AI.

        The service arguments remain accepted for compatibility with older callers.
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
            
            # Count current members without broadening any member's sharing scope.
            members = db.query(FamilyMemberDB).filter(
                and_(
                    FamilyMemberDB.family_id == family_id,
                    FamilyMemberDB.status == "active"
                )
            ).all()
            
            if period not in {"daily", "weekly"}:
                raise ValidationError("Choose a daily or weekly family overview")
            japan = timezone(timedelta(hours=9))
            today = datetime.now(japan).date()
            first_day = today - timedelta(days=0 if period == "daily" else 6)
            shared_data = self.get_shared_tracking_data(family_id, user_id,
                days=2 if period == "daily" else FAMILY_SHARED_DAYS, db=db)
            shared_data = [entry for entry in shared_data if first_day <= datetime.fromisoformat(
                entry["timestamp"]).replace(tzinfo=timezone.utc).astimezone(japan).date() <= today]
            # Sharing never grants AI permission or access to excluded categories.
            summary = {"from": first_day.isoformat(), "through": today.isoformat(),
                "record_counts": {kind: sum(entry["entry_type"] == kind for entry in shared_data)
                for kind in CARE_TYPES | PARENT_TYPES}}
            
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
        share_enabled: bool = False,
        db: Optional[Session] = None,
        share_baby: Optional[bool] = None,
        share_parent: bool = False,
        share_notes: bool = False,
        display_label: str = "",
        *,
        expected_revision: int,
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
            if member.revision != expected_revision:
                raise ConflictError("Membership or sharing changed; review the latest settings")
            
            # Update permissions
            baby = share_enabled is True if share_baby is None else share_baby is True
            permissions = {"share_tracking": False, "share_baby": baby,
                "share_parent": share_parent is True, "share_notes": share_notes is True,
                "display_label": display_label}
            changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == member.id,
                FamilyMemberDB.status == "active", FamilyMemberDB.revision == expected_revision,
            ).update({"permissions": permissions, "revision": expected_revision + 1}, synchronize_session=False)
            if changed != 1:
                raise ConflictError("Membership or sharing changed; review the latest settings")
            db.commit()
            
            return {
                "family_id": family_id,
                "user_id": user_id,
                "share_enabled": baby or share_parent is True,
                "permissions": permissions,
                "revision": expected_revision + 1,
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
