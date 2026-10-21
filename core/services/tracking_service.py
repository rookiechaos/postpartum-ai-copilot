"""
Tracking Service - Manages tracking entries and user context
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from hashlib import sha256
import json
from sqlalchemy.exc import IntegrityError
from models.database import TrackingEntryDB, TrackingWriteDB, UserContextDB
from models.schemas import TrackingEntry, TrackingEntryUpdate
from exceptions import DatabaseError, ValidationError, NotFoundError, ConflictError
from utils.db_helpers import query_in_executor
from services.tracking_policy import validate_record_time, validate_record_interval
from services.care_subjects import validate_attribution, owned_record_metadata
from services.ai_data_scope import PARENT_TYPES


class TrackingService:
    """Service for managing tracking data"""

    async def update_entry(self, entry_id: int, user_id: str, entry: TrackingEntryUpdate, db: Session) -> Dict[str, Any]:
        """Replace an owned record; record identity and ownership are immutable."""
        timestamp = validate_record_time(entry.timestamp) if entry.timestamp is not None else None

        def _update_entry():
            record = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.id == entry_id, TrackingEntryDB.user_id == user_id
            ).first()
            if record is None:
                db.rollback()
                return "missing", None
            if record.record_key != str(entry.record_key) or record.revision != entry.revision:
                db.rollback()
                return "conflict", None
            values = entry.model_dump(exclude={"id", "user_id", "record_key", "revision", "timestamp", "sharing_revision", "subject_name"}, mode="python")
            values = {key: value.value if hasattr(value, "value") else value for key, value in values.items()}
            for field in ("subject_id", "family_shared", "end_timestamp"):
                if field not in entry.model_fields_set and values["entry_type"] == record.entry_type:
                    values[field] = getattr(record, field)
            values["subject_id"] = str(values["subject_id"]) if values.get("subject_id") else None
            values.update(timestamp=timestamp or record.timestamp, revision=entry.revision + 1)
            validate_record_interval(values)
            validate_attribution(db, user_id, values, entry.sharing_revision)
            # Snapshot before committing; never refetch a possibly reused numeric ID.
            result = self._entry_to_dict(record)
            result.update(values)
            result["timestamp"] = values["timestamp"].isoformat()
            result["end_timestamp"] = values["end_timestamp"].isoformat() if values.get("end_timestamp") else None
            metadata = owned_record_metadata(db, user_id).get(values["subject_id"], {})
            result.update(subject_name=metadata.get("nickname"), sharing_revision=metadata.get("sharing_revision"))
            affected = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.id == entry_id, TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.record_key == str(entry.record_key), TrackingEntryDB.revision == entry.revision,
            ).update(values, synchronize_session=False)
            if affected != 1:
                db.rollback()
                return "conflict", None
            db.commit()
            return "updated", result

        status, result = await query_in_executor(_update_entry, db, error_message="Failed to update tracking entry")
        if status == "missing":
            raise NotFoundError("Tracking entry not found")
        if status == "conflict":
            raise ConflictError("Tracking entry has changed; reload it before editing")
        return result

    async def delete_entry(self, entry_id: int, user_id: str, record_key: str, revision: int, db: Session) -> Dict[str, Any]:
        """Delete only the caller's record without returning another owner's data."""
        def _delete_entry():
            record = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.id == entry_id, TrackingEntryDB.user_id == user_id
            ).first()
            if record is None:
                db.rollback()
                return "missing"
            affected = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.id == entry_id, TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.record_key == record_key, TrackingEntryDB.revision == revision,
            ).delete(synchronize_session=False)
            if affected != 1:
                db.rollback()
                return "conflict"
            db.commit()
            return "deleted"

        result = await query_in_executor(_delete_entry, db, error_message="Failed to delete tracking entry")
        if result == "missing":
            raise NotFoundError("Tracking entry not found")
        if result == "conflict":
            raise ConflictError("Tracking entry has changed; reload it before deleting")
        return {"deleted": True}
    
    async def add_entry(
        self,
        entry: TrackingEntry,
        db: Session
    ) -> Dict[str, Any]:
        """Add a new tracking entry"""
        timestamp = validate_record_time(entry.timestamp)
        request_key = str(entry.request_key) if getattr(entry, "request_key", None) else None
        if request_key and entry.timestamp is None:
            raise ValidationError("Retryable writes require an explicit record timestamp")
        values = entry.model_dump(exclude={"id", "user_id", "record_key", "revision", "request_key", "sharing_revision", "subject_name"}, mode="python")
        values = {key: value.value if hasattr(value, "value") else value for key, value in values.items()}
        values["subject_id"] = str(values["subject_id"]) if values.get("subject_id") else None
        values["timestamp"] = timestamp
        validate_record_interval(values)
        fingerprint_values = {key: value.isoformat() if isinstance(value, datetime) else value for key, value in values.items()}
        # Keep pre-attribution creation receipts retryable without changing their fingerprint.
        for key in ("subject_id", "family_shared", "end_timestamp"):
            if key not in entry.model_fields_set:
                fingerprint_values.pop(key, None)
        fingerprint = sha256(json.dumps(fingerprint_values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

        def _receipt():
            receipt = db.get(TrackingWriteDB, (entry.user_id, request_key))
            if receipt is None:
                return None
            if receipt.fingerprint != fingerprint:
                return "conflict", None
            present = db.query(TrackingEntryDB.id).filter(
                TrackingEntryDB.user_id == entry.user_id, TrackingEntryDB.record_key == receipt.record_key,
            ).first()
            return ("saved", receipt.result) if present else ("deleted", None)

        def _add_entry():
            if request_key:
                previous = _receipt()
                if previous is not None:
                    db.rollback()
                    return previous
            validate_attribution(db, entry.user_id, values, entry.sharing_revision)
            db_entry = TrackingEntryDB(
                user_id=entry.user_id,
                entry_type=entry.entry_type.value,
                timestamp=timestamp,
                subject_id=values["subject_id"], family_shared=values["family_shared"], end_timestamp=values["end_timestamp"],
                feeding_type=entry.feeding_type.value if entry.feeding_type else None,
                duration_minutes=values["duration_minutes"],
                amount_ml=entry.amount_ml,
                side=entry.side,
                diaper_type=entry.diaper_type.value if entry.diaper_type else None,
                sleep_duration_minutes=values["sleep_duration_minutes"],
                sleep_quality=entry.sleep_quality,
                mood_level=entry.mood_level.value if entry.mood_level else None,
                mood_notes=entry.mood_notes,
                pumped_amount_ml=entry.pumped_amount_ml,
                weight_kg=entry.weight_kg,
                breast_condition=entry.breast_condition,
                recovery_notes=entry.recovery_notes,
                notes=entry.notes
            )
            
            db.add(db_entry)
            db.flush()
            subject = owned_record_metadata(db, entry.user_id).get(db_entry.subject_id, {})
            result = {
                "id": db_entry.id,
                "record_key": db_entry.record_key,
                "revision": db_entry.revision,
                "message": "Entry added successfully",
                "timestamp": db_entry.timestamp.isoformat(),
                "end_timestamp": db_entry.end_timestamp.isoformat() if db_entry.end_timestamp else None,
                "subject_id": db_entry.subject_id, "family_shared": db_entry.family_shared,
                "subject_name": subject.get("nickname"), "sharing_revision": subject.get("sharing_revision"),
            }
            if request_key:
                db.add(TrackingWriteDB(user_id=entry.user_id, request_key=request_key,
                    fingerprint=fingerprint, record_key=db_entry.record_key, result=result))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                previous = _receipt() if request_key else None
                if previous is None:
                    raise
                db.rollback()
                return previous
            return "saved", result
        
        status, result = await query_in_executor(
            _add_entry,
            db,
            error_message="Failed to add tracking entry"
        )
        if status == "conflict":
            raise ConflictError("This save request already has different content")
        if status == "deleted":
            raise ConflictError("This save request belongs to a deleted record")
        return result
    
    async def get_entries(
        self,
        user_id: str,
        db: Session,
        days: int = 7,
        subject_id: Optional[str] = None,
        unassigned: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get tracking entries for a user"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        def _get_entries():
            query = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                or_(TrackingEntryDB.timestamp >= cutoff_date, TrackingEntryDB.end_timestamp >= cutoff_date)
            )
            if subject_id is not None or unassigned:
                care_scope = TrackingEntryDB.subject_id == subject_id if subject_id is not None else TrackingEntryDB.subject_id.is_(None)
                query = query.filter(or_(TrackingEntryDB.entry_type.in_(PARENT_TYPES), care_scope))
            entries = query.order_by(desc(TrackingEntryDB.timestamp)).all()
            return self._owned_entries(entries, db, user_id)
        
        return await query_in_executor(
            _get_entries,
            db,
            error_message=f"Failed to get tracking entries for user {user_id}"
        )
    
    async def get_latest_entries(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        def _latest():
            rows = db.query(TrackingEntryDB).filter(TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.timestamp >= datetime.utcnow() - timedelta(days=365),
            ).order_by(desc(TrackingEntryDB.timestamp), desc(TrackingEntryDB.id)).limit(6).all()
            return self._owned_entries(rows, db, user_id)
        return await query_in_executor(_latest, db, error_message="Failed to load recent records")

    async def get_recent_entries(
        self,
        user_id: str,
        db: Session,
        hours: int = 6
    ) -> List[Dict[str, Any]]:
        """Get recent entries within specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        def _get_recent_entries():
            entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.timestamp >= cutoff_time
            ).order_by(desc(TrackingEntryDB.timestamp)).all()
            return [self._entry_to_dict(entry) for entry in entries]
        
        return await query_in_executor(
            _get_recent_entries,
            db,
            error_message=f"Failed to get recent entries for user {user_id}"
        )
    
    async def get_mood_history(
        self,
        user_id: str,
        db: Session,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get mood tracking history"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        def _get_mood_history():
            entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.entry_type == "mood",
                TrackingEntryDB.timestamp >= cutoff_date
            ).order_by(desc(TrackingEntryDB.timestamp)).all()
            return [self._entry_to_dict(entry) for entry in entries]
        
        return await query_in_executor(
            _get_mood_history,
            db,
            error_message=f"Failed to get mood history for user {user_id}"
        )
    
    async def get_user_context(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Read current account context in API and independent worker processes."""
        def _get_context():
            context_db = db.query(UserContextDB).filter(
                UserContextDB.user_id == user_id
            ).populate_existing().first()
            
            if context_db:
                context = context_db.context or {}
            else:
                # Return default context
                context = {
                    "baby_age_days": None,
                    "birth_type": None,
                    "feeding_type": None,
                    "sleep_hours_avg": None
                }
            
            return context
        
        return await query_in_executor(
            _get_context,
            db,
            error_message=f"Failed to get user context for user {user_id}"
        )
    
    async def update_user_context(
        self,
        user_id: str,
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Update supplied context fields while preserving omitted fields."""
        # Get old context to check for language changes
        def _get_old_context():
            user_context = db.query(UserContextDB).filter(
                UserContextDB.user_id == user_id
            ).first()
            return user_context.context if user_context else None
        
        old_context = await query_in_executor(
            _get_old_context,
            db,
            error_message=f"Failed to get old context for user {user_id}"
        )
        
        def _update_context():
            context_db = db.query(UserContextDB).filter(
                UserContextDB.user_id == user_id
            ).first()
            
            if context_db:
                context_db.context = {**(context_db.context or {}), **context}
                context_db.updated_at = datetime.utcnow()
            else:
                context_db = UserContextDB(
                    user_id=user_id,
                    context=context
                )
                db.add(context_db)
            
            db.commit()
            db.refresh(context_db)
            
            return context_db.context
        
        updated_context = await query_in_executor(
            _update_context,
            db,
            error_message=f"Failed to update user context for user {user_id}"
        )
        
        # Invalidate language cache if language changed
        old_language = old_context.get("language") if old_context else None
        new_language = updated_context.get("language")
        if old_language != new_language:
            from utils.user_preferences import invalidate_language_cache
            invalidate_language_cache(user_id)
        
        return {
            "message": "Context updated successfully",
            "context": updated_context
        }
    
    def _entry_to_dict(self, entry: TrackingEntryDB) -> Dict[str, Any]:
        """Convert database entry to dictionary"""
        return {
            "id": entry.id,
            "record_key": entry.record_key,
            "revision": entry.revision,
            "user_id": entry.user_id,
            "entry_type": entry.entry_type,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "end_timestamp": entry.end_timestamp.isoformat() if entry.end_timestamp else None,
            "subject_id": entry.subject_id, "family_shared": entry.family_shared,
            "feeding_type": entry.feeding_type,
            "duration_minutes": entry.duration_minutes,
            "amount_ml": entry.amount_ml,
            "side": entry.side,
            "diaper_type": entry.diaper_type,
            "sleep_duration_minutes": entry.sleep_duration_minutes,
            "sleep_quality": entry.sleep_quality,
            "mood_level": entry.mood_level,
            "mood_notes": entry.mood_notes,
            "pumped_amount_ml": entry.pumped_amount_ml,
            "weight_kg": entry.weight_kg,
            "breast_condition": entry.breast_condition,
            "recovery_notes": entry.recovery_notes,
            "notes": entry.notes
        }

    def _owned_entries(self, entries, db, user_id):
        subjects = owned_record_metadata(db, user_id)
        result = []
        for entry in entries:
            subject = subjects.get(entry.subject_id, {})
            result.append({**self._entry_to_dict(entry), "subject_name": subject.get("nickname"),
                "sharing_revision": subject.get("sharing_revision")})
        return result
    
    async def get_weight_trends(
        self,
        user_id: str,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get weight trends for a user"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        def _get_weight_trends():
            entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.weight_kg.isnot(None),
                TrackingEntryDB.timestamp >= cutoff_date
            ).order_by(TrackingEntryDB.timestamp).all()
            
            if not entries:
                return {
                    "trend": "no_data",
                    "entries": [],
                    "average_weight": None,
                    "weight_change": None
                }
            
            weights = [e.weight_kg for e in entries if e.weight_kg]
            if not weights:
                return {
                    "trend": "no_data",
                    "entries": [],
                    "average_weight": None,
                    "weight_change": None
                }
            
            first_weight = weights[0]
            last_weight = weights[-1]
            weight_change = last_weight - first_weight
            
            return {
                "trend": "increasing" if weight_change > 0 else "decreasing" if weight_change < 0 else "stable",
                "entries": [{"date": e.timestamp.isoformat() if e.timestamp else None, "weight_kg": e.weight_kg} for e in entries if e.weight_kg],
                "average_weight": sum(weights) / len(weights),
                "weight_change": weight_change,
                "first_weight": first_weight,
                "last_weight": last_weight
            }
        
        return await query_in_executor(
            _get_weight_trends,
            db,
            error_message=f"Failed to get weight trends for user {user_id}"
        )
    
    async def get_recovery_trends(
        self,
        user_id: str,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get recovery trends (breast condition, recovery notes)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        def _get_recovery_trends():
            entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                or_(
                    TrackingEntryDB.breast_condition.isnot(None),
                    TrackingEntryDB.recovery_notes.isnot(None)
                ),
                TrackingEntryDB.timestamp >= cutoff_date
            ).order_by(TrackingEntryDB.timestamp).all()
            
            if not entries:
                return {
                    "trend": "no_data",
                    "entries": [],
                    "breast_condition_summary": {}
                }
            
            # Analyze breast condition trends
            breast_conditions = {}
            for e in entries:
                if e.breast_condition:
                    breast_conditions[e.breast_condition] = breast_conditions.get(e.breast_condition, 0) + 1
            
            return {
                "trend": "improving" if "normal" in breast_conditions else "needs_attention",
                "entries": [{
                    "date": e.timestamp.isoformat() if e.timestamp else None,
                    "breast_condition": e.breast_condition,
                    "recovery_notes": e.recovery_notes
                } for e in entries],
                "breast_condition_summary": breast_conditions,
                "total_entries": len(entries)
            }
        
        return await query_in_executor(
            _get_recovery_trends,
            db,
            error_message=f"Failed to get recovery trends for user {user_id}"
        )
    
    async def _calendar_summary(self, user_id: str, db: Session, period: str) -> Dict[str, Any]:
        """Count owned records in Japan calendar periods without an AI call or stale cache."""
        japan = timezone(timedelta(hours=9))
        today = datetime.now(japan).date()
        first_day = today if period == "daily" else today - timedelta(days=today.weekday())
        start = datetime.combine(first_day, datetime.min.time(), tzinfo=japan).astimezone(timezone.utc).replace(tzinfo=None)
        end = start + timedelta(days=1 if period == "daily" else 7)

        def _counts():
            rows = db.query(TrackingEntryDB.entry_type, func.count(TrackingEntryDB.id)).filter(
                TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.timestamp >= start,
                TrackingEntryDB.timestamp < end,
            ).group_by(TrackingEntryDB.entry_type).all()
            return {kind: count for kind, count in rows}

        counts = await query_in_executor(_counts, db, error_message="Failed to count care records")
        context = await self.get_user_context(user_id, db)
        language = context.get("language")
        japanese = not isinstance(language, str) or language.startswith("ja")
        total = sum(counts.values())
        label = "今日" if period == "daily" else "今週"
        english_label = "today" if period == "daily" else "this week"
        return {
            "period": period,
            "date" if period == "daily" else "week_start": first_day.isoformat(),
            "entries_count": total,
            "record_counts": counts,
            "summary": (f"{label}記録した件数は{total}件です。未記録の内容は含みません。" if japanese else
                        f"Recorded {total} entries {english_label}. Unrecorded care is unknown."),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    async def generate_daily_summary(self, user_id: str, db: Session, ai_service=None) -> Dict[str, Any]:
        """Read local statistics. The legacy ai_service argument is ignored for privacy."""
        return await self._calendar_summary(user_id, db, "daily")

    async def generate_weekly_summary(self, user_id: str, db: Session, ai_service=None) -> Dict[str, Any]:
        """Read local weekly statistics; AI analysis requires the separate scoped action."""
        return await self._calendar_summary(user_id, db, "weekly")
