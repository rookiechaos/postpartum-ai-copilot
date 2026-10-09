"""
Tracking Service - Manages tracking entries and user context
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from models.database import TrackingEntryDB, UserContextDB
from models.schemas import TrackingEntry
from exceptions import DatabaseError, ValidationError
from utils.db_helpers import query_in_executor


class TrackingService:
    """Service for managing tracking data"""
    
    async def add_entry(
        self,
        entry: TrackingEntry,
        db: Session
    ) -> Dict[str, Any]:
        """Add a new tracking entry"""
        def _add_entry():
            db_entry = TrackingEntryDB(
                user_id=entry.user_id,
                entry_type=entry.entry_type.value,
                timestamp=entry.timestamp or datetime.utcnow(),
                feeding_type=entry.feeding_type.value if entry.feeding_type else None,
                duration_minutes=entry.duration_minutes,
                amount_ml=entry.amount_ml,
                side=entry.side,
                diaper_type=entry.diaper_type.value if entry.diaper_type else None,
                sleep_duration_minutes=entry.sleep_duration_minutes,
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
            db.commit()
            db.refresh(db_entry)
            
            return {
                "id": db_entry.id,
                "message": "Entry added successfully",
                "timestamp": db_entry.timestamp.isoformat()
            }
        
        return await query_in_executor(
            _add_entry,
            db,
            error_message="Failed to add tracking entry"
        )
    
    async def get_entries(
        self,
        user_id: str,
        db: Session,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get tracking entries for a user"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        def _get_entries():
            entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.timestamp >= cutoff_date
            ).order_by(desc(TrackingEntryDB.timestamp)).all()
            return [self._entry_to_dict(entry) for entry in entries]
        
        return await query_in_executor(
            _get_entries,
            db,
            error_message=f"Failed to get tracking entries for user {user_id}"
        )
    
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
        """Get user context (baby age, birth type, etc.)"""
        # Try cache first
        from services.cache_service import get_cache
        cache = get_cache()
        cache_key = f"user_context:{user_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        def _get_context():
            context_db = db.query(UserContextDB).filter(
                UserContextDB.user_id == user_id
            ).first()
            
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
        
        context = await query_in_executor(
            _get_context,
            db,
            error_message=f"Failed to get user context for user {user_id}"
        )
        # Cache for 30 minutes
        cache.set(cache_key, context, ttl=1800)
        return context
    
    async def update_user_context(
        self,
        user_id: str,
        context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Update user context"""
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
                context_db.context = context
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
        
        # Update cache
        from services.cache_service import get_cache
        cache = get_cache()
        cache_key = f"user_context:{user_id}"
        cache.set(cache_key, updated_context, ttl=1800)
        
        # Invalidate language cache if language changed
        old_language = old_context.get("language") if old_context else None
        new_language = context.get("language")
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
            "user_id": entry.user_id,
            "entry_type": entry.entry_type,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
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
    
    async def generate_daily_summary(
        self,
        user_id: str,
        db: Session,
        ai_service = None
    ) -> Dict[str, Any]:
        """Generate daily summary of tracking data with caching"""
        # Get today's entries
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        # Check cache first (cache key includes date to ensure daily refresh)
        from services.cache_service import get_cache
        cache = get_cache()
        cache_key = f"daily_summary:{user_id}:{today.isoformat()}"
        cached_summary = cache.get(cache_key)
        if cached_summary is not None:
            return cached_summary
        
        def _get_daily_entries():
            entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.timestamp >= start_of_day
            ).order_by(TrackingEntryDB.timestamp).all()
            return [self._entry_to_dict(e) for e in entries]
        
        entries = await query_in_executor(
            _get_daily_entries,
            db,
            error_message=f"Failed to get daily entries for user {user_id}"
        )
        
        # Get user context
        context = await self.get_user_context(user_id, db)
        
        # Generate AI summary if ai_service is provided
        if ai_service:
            language = context.get("language", "en") or "en"
            summary = await ai_service.generate_tracking_summary(
                entries=entries,
                context=context,
                period="daily",
                language=language
            )
            result = {
                "period": "daily",
                "date": today.isoformat(),
                "entries_count": len(entries),
                "summary": summary.get("summary_text", ""),
                "timestamp": summary.get("timestamp")
            }
        else:
            # Basic summary without AI
            result = {
                "period": "daily",
                "date": today.isoformat(),
                "entries_count": len(entries),
                "summary": f"You tracked {len(entries)} entries today. You're doing great!",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Cache the result (TTL: 1 hour, but will be invalidated by date in key)
        # Use longer TTL since the date in key ensures daily refresh
        cache.set(cache_key, result, ttl=3600)
        return result
    
    async def generate_weekly_summary(
        self,
        user_id: str,
        db: Session,
        ai_service = None
    ) -> Dict[str, Any]:
        """Generate weekly summary of tracking data with caching"""
        # Get this week's entries
        today = datetime.utcnow().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week_datetime = datetime.combine(start_of_week, datetime.min.time())
        
        # Check cache first (cache key includes week start date to ensure weekly refresh)
        from services.cache_service import get_cache
        cache = get_cache()
        cache_key = f"weekly_summary:{user_id}:{start_of_week.isoformat()}"
        cached_summary = cache.get(cache_key)
        if cached_summary is not None:
            return cached_summary
        
        def _get_weekly_entries():
            entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.timestamp >= start_of_week_datetime
            ).order_by(TrackingEntryDB.timestamp).all()
            return [self._entry_to_dict(e) for e in entries]
        
        entries = await query_in_executor(
            _get_weekly_entries,
            db,
            error_message=f"Failed to get weekly entries for user {user_id}"
        )
        
        # Get user context
        context = await self.get_user_context(user_id, db)
        
        # Generate AI summary if ai_service is provided
        if ai_service:
            language = context.get("language", "en") or "en"
            summary = await ai_service.generate_tracking_summary(
                entries=entries,
                context=context,
                period="weekly",
                language=language
            )
            result = {
                "period": "weekly",
                "week_start": start_of_week.isoformat(),
                "entries_count": len(entries),
                "summary": summary.get("summary_text", ""),
                "timestamp": summary.get("timestamp")
            }
        else:
            # Basic summary without AI
            result = {
                "period": "weekly",
                "week_start": start_of_week.isoformat(),
                "entries_count": len(entries),
                "summary": f"You tracked {len(entries)} entries this week. Keep up the great work!",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Cache the result (TTL: 6 hours, but will be invalidated by week start date in key)
        # Use longer TTL since the week start date in key ensures weekly refresh
        cache.set(cache_key, result, ttl=21600)
        return result