"""
Product Analytics Service - Product-level metrics and analysis
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, distinct
from collections import defaultdict
import uuid

from models.analytics_models import UserEventDB, UserSessionDB, ProductMetricsDB
from models.database import UserDB, TaskDB, TrackingEntryDB, SessionLocal
from services.logging_service import logger
from exceptions import DatabaseError


class ProductAnalyticsService:
    """Service for product-level analytics and metrics"""
    
    def track_event(
        self,
        user_id: Optional[str],
        event_type: str,
        event_name: str,
        event_category: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        properties: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        page_url: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Track a user event"""
        try:
            event_id = f"event_{uuid.uuid4().hex[:12]}"
            
            event = UserEventDB(
                event_id=event_id,
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                event_name=event_name,
                event_category=event_category,
                event_data=event_data,
                properties=properties,
                page_url=page_url
            )
            
            db.add(event)
            db.commit()
            
            return {"event_id": event_id, "status": "tracked"}
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "track_event"})
            raise DatabaseError(f"Failed to track event: {str(e)}")
    
    def get_dau(self, date: Optional[datetime] = None, db: Session = None) -> int:
        """Get Daily Active Users for a date"""
        try:
            if date is None:
                target_date = datetime.utcnow().date()
            elif isinstance(date, datetime):
                target_date = date.date()
            else:
                target_date = date
            
            start = datetime.combine(target_date, datetime.min.time())
            end = datetime.combine(target_date, datetime.max.time())
            
            # Count unique users who had events or sessions on this date
            unique_users = db.query(func.count(func.distinct(UserEventDB.user_id))).filter(
                and_(
                    UserEventDB.created_at >= start,
                    UserEventDB.created_at <= end,
                    UserEventDB.user_id.isnot(None)
                )
            ).scalar()
            
            return unique_users or 0
        except Exception as e:
            logger.log_error(e, context={"action": "get_dau"})
            return 0
    
    def get_mau(self, month: Optional[datetime] = None, db: Session = None) -> int:
        """Get Monthly Active Users for a month"""
        try:
            if month is None:
                month = datetime.utcnow()
            
            start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month.month == 12:
                end = month.replace(year=month.year + 1, month=1, day=1)
            else:
                end = month.replace(month=month.month + 1, day=1)
            
            unique_users = db.query(func.count(func.distinct(UserEventDB.user_id))).filter(
                and_(
                    UserEventDB.created_at >= start,
                    UserEventDB.created_at < end,
                    UserEventDB.user_id.isnot(None)
                )
            ).scalar()
            
            return unique_users or 0
        except Exception as e:
            logger.log_error(e, context={"action": "get_mau"})
            return 0
    
    def get_retention_rate(
        self,
        cohort_date: datetime,
        days: int = 7,
        db: Session = None
    ) -> float:
        """Calculate retention rate for a cohort"""
        try:
            # Get users who registered on cohort_date
            cohort_start = cohort_date.replace(hour=0, minute=0, second=0, microsecond=0)
            cohort_end = cohort_start + timedelta(days=1)
            
            # Get users from UserDB table
            cohort_users = db.query(UserDB.user_id).filter(
                and_(
                    UserDB.created_at >= cohort_start,
                    UserDB.created_at < cohort_end
                )
            ).all()
            
            cohort_user_ids = [u[0] for u in cohort_users if u[0]]
            
            if not cohort_user_ids:
                return 0.0
            
            # Check how many returned after N days (within a window)
            retention_start = cohort_start + timedelta(days=days)
            retention_end = retention_start + timedelta(days=1)
            
            returned_users = db.query(func.count(func.distinct(UserEventDB.user_id))).filter(
                and_(
                    UserEventDB.user_id.in_(cohort_user_ids),
                    UserEventDB.created_at >= retention_start,
                    UserEventDB.created_at < retention_end
                )
            ).scalar()
            
            return (returned_users / len(cohort_user_ids)) * 100 if cohort_user_ids else 0.0
        except Exception as e:
            logger.log_error(e, context={"action": "get_retention_rate"})
            return 0.0
    
    def get_retention_analysis(
        self,
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive retention analysis
        
        Returns:
            - Day 1, 7, 14, 30 retention rates
            - Cohort-based retention
            - Retention trends
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all cohorts in the period
            cohorts = db.query(
                func.date(UserDB.created_at).label('cohort_date'),
                func.count(UserDB.user_id).label('cohort_size')
            ).filter(
                UserDB.created_at >= cutoff_date
            ).group_by(func.date(UserDB.created_at)).all()
            
            retention_data = {
                "day_1": [],
                "day_7": [],
                "day_14": [],
                "day_30": []
            }
            
            for cohort_date, cohort_size in cohorts:
                if cohort_size == 0:
                    continue
                
                cohort_datetime = datetime.combine(cohort_date, datetime.min.time())
                
                # Calculate retention for different days
                for day in [1, 7, 14, 30]:
                    if (datetime.utcnow() - cohort_datetime).days >= day:
                        rate = self.get_retention_rate(cohort_datetime, days=day, db=db)
                        retention_data[f"day_{day}"].append({
                            "cohort_date": cohort_date.isoformat() if isinstance(cohort_date, datetime) else str(cohort_date),
                            "cohort_size": cohort_size,
                            "retention_rate": round(rate, 2)
                        })
            
            # Calculate average retention rates
            avg_retention = {
                "day_1": sum(r["retention_rate"] for r in retention_data["day_1"]) / len(retention_data["day_1"]) if retention_data["day_1"] else 0,
                "day_7": sum(r["retention_rate"] for r in retention_data["day_7"]) / len(retention_data["day_7"]) if retention_data["day_7"] else 0,
                "day_14": sum(r["retention_rate"] for r in retention_data["day_14"]) / len(retention_data["day_14"]) if retention_data["day_14"] else 0,
                "day_30": sum(r["retention_rate"] for r in retention_data["day_30"]) / len(retention_data["day_30"]) if retention_data["day_30"] else 0
            }
            
            return {
                "average_retention": avg_retention,
                "cohort_retention": retention_data,
                "period_days": days
            }
        except Exception as e:
            logger.log_error(e, context={"action": "get_retention_analysis"})
            return {
                "average_retention": {"day_1": 0, "day_7": 0, "day_14": 0, "day_30": 0},
                "cohort_retention": {},
                "period_days": days
            }
    
    def get_conversion_funnel(
        self,
        days: int = 7,
        db: Session = None
    ) -> Dict[str, Any]:
        """Calculate conversion funnel"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Step 1: Registered users (tracked via events)
            registered = db.query(func.count(func.distinct(UserEventDB.user_id))).filter(
                and_(
                    UserEventDB.event_name == "user_registered",
                    UserEventDB.created_at >= cutoff_date,
                    UserEventDB.user_id.isnot(None)
                )
            ).scalar() or 0
            
            # Step 2: Completed onboarding
            completed_onboarding = db.query(func.count(func.distinct(UserEventDB.user_id))).filter(
                and_(
                    UserEventDB.event_name == "onboarding_completed",
                    UserEventDB.created_at >= cutoff_date
                )
            ).scalar() or 0
            
            # Step 3: First tracking entry
            first_tracking = db.query(func.count(func.distinct(TrackingEntryDB.user_id))).filter(
                TrackingEntryDB.timestamp >= cutoff_date
            ).scalar() or 0
            
            # Step 4: First chat
            first_chat = db.query(func.count(func.distinct(TaskDB.user_id))).filter(
                and_(
                    TaskDB.task_type == "ai_chat",
                    TaskDB.created_at >= cutoff_date
                )
            ).scalar() or 0
            
            # Step 5: Active user (3+ days of activity)
            active_users = db.query(func.count(func.distinct(UserEventDB.user_id))).filter(
                and_(
                    UserEventDB.created_at >= cutoff_date,
                    UserEventDB.user_id.isnot(None)
                )
            ).group_by(UserEventDB.user_id).having(func.count(func.distinct(func.date(UserEventDB.created_at))) >= 3).count()
            
            return {
                "registered": registered,
                "completed_onboarding": completed_onboarding,
                "first_tracking": first_tracking,
                "first_chat": first_chat,
                "active_users": active_users,
                "onboarding_rate": (completed_onboarding / registered * 100) if registered > 0 else 0,
                "tracking_rate": (first_tracking / registered * 100) if registered > 0 else 0,
                "chat_rate": (first_chat / registered * 100) if registered > 0 else 0,
                "activation_rate": (active_users / registered * 100) if registered > 0 else 0
            }
        except Exception as e:
            logger.log_error(e, context={"action": "get_conversion_funnel"})
            return {}
    
    def get_feature_usage(
        self,
        days: int = 7,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get feature usage statistics"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Count events by category/name
            feature_usage = db.query(
                UserEventDB.event_category,
                UserEventDB.event_name,
                func.count(UserEventDB.id).label('count')
            ).filter(
                UserEventDB.created_at >= cutoff_date
            ).group_by(
                UserEventDB.event_category,
                UserEventDB.event_name
            ).all()
            
            usage_dict = defaultdict(int)
            for category, name, count in feature_usage:
                key = f"{category}:{name}" if category else name
                usage_dict[key] = count
            
            # Also count by task types
            task_usage = db.query(
                TaskDB.task_type,
                func.count(TaskDB.id).label('count')
            ).filter(
                TaskDB.created_at >= cutoff_date
            ).group_by(TaskDB.task_type).all()
            
            for task_type, count in task_usage:
                usage_dict[f"task:{task_type}"] = count
            
            return dict(usage_dict)
        except Exception as e:
            logger.log_error(e, context={"action": "get_feature_usage"})
            return {}
    
    def get_user_path_analysis(
        self,
        user_id: str,
        days: int = 7,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Analyze user path through the application"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            events = db.query(UserEventDB).filter(
                and_(
                    UserEventDB.user_id == user_id,
                    UserEventDB.created_at >= cutoff_date
                )
            ).order_by(UserEventDB.created_at).all()
            
            path = []
            for event in events:
                path.append({
                    "event_type": event.event_type,
                    "event_name": event.event_name,
                    "page_url": event.page_url,
                    "timestamp": event.created_at.isoformat() if event.created_at else None
                })
            
            return path
        except Exception as e:
            logger.log_error(e, context={"action": "get_user_path_analysis"})
            return []
    
    def calculate_daily_metrics(
        self,
        date: Optional[datetime] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Calculate and store daily product metrics"""
        try:
            if date is None:
                date = datetime.utcnow()
            
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Calculate metrics
            dau = self.get_dau(date.date(), db)
            mau = self.get_mau(date, db)
            
            # New users (tracked via events)
            new_users = db.query(func.count(func.distinct(UserEventDB.user_id))).filter(
                and_(
                    UserEventDB.event_name == "user_registered",
                    UserEventDB.created_at >= date_start,
                    UserEventDB.created_at <= date_end,
                    UserEventDB.user_id.isnot(None)
                )
            ).scalar() or 0
            
            # Sessions
            sessions = db.query(func.count(UserSessionDB.session_id)).filter(
                and_(
                    UserSessionDB.started_at >= date_start,
                    UserSessionDB.started_at <= date_end
                )
            ).scalar() or 0
            
            # Feature usage
            feature_usage = self.get_feature_usage(days=1, db=db)
            
            # Store or update metrics
            existing = db.query(ProductMetricsDB).filter(
                func.date(ProductMetricsDB.date) == date.date()
            ).first()
            
            if existing:
                existing.dau = dau
                existing.mau = mau
                existing.new_users = new_users
                existing.total_sessions = sessions
                existing.feature_usage = feature_usage
            else:
                metrics = ProductMetricsDB(
                    date=date_start,
                    dau=dau,
                    mau=mau,
                    new_users=new_users,
                    total_sessions=sessions,
                    feature_usage=feature_usage
                )
                db.add(metrics)
            
            db.commit()
            
            return {
                "date": date_start.isoformat(),
                "dau": dau,
                "mau": mau,
                "new_users": new_users,
                "total_sessions": sessions,
                "feature_usage": feature_usage
            }
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "calculate_daily_metrics"})
            raise DatabaseError(f"Failed to calculate daily metrics: {str(e)}")
    
    def get_product_dashboard(
        self,
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get comprehensive product dashboard data"""
        try:
            # Current metrics
            dau = self.get_dau(db=db)
            mau = self.get_mau(db=db)
            
            # Conversion funnel
            funnel = self.get_conversion_funnel(days=days, db=db)
            
            # Feature usage
            feature_usage = self.get_feature_usage(days=days, db=db)
            
            # Retention rates
            retention_7d = self.get_retention_rate(
                datetime.utcnow() - timedelta(days=7),
                days=7,
                db=db
            )
            retention_30d = self.get_retention_rate(
                datetime.utcnow() - timedelta(days=30),
                days=30,
                db=db
            )
            
            # Historical DAU/MAU
            historical = db.query(ProductMetricsDB).filter(
                ProductMetricsDB.date >= datetime.utcnow() - timedelta(days=days)
            ).order_by(ProductMetricsDB.date).all()
            
            historical_data = [
                {
                    "date": m.date.isoformat() if m.date else None,
                    "dau": m.dau,
                    "mau": m.mau,
                    "new_users": m.new_users
                }
                for m in historical
            ]
            
            return {
                "current": {
                    "dau": dau,
                    "mau": mau,
                    "dau_mau_ratio": (dau / mau * 100) if mau > 0 else 0
                },
                "conversion_funnel": funnel,
                "feature_usage": feature_usage,
                "retention": {
                    "day_7": retention_7d,
                    "day_30": retention_30d
                },
                "historical": historical_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.log_error(e, context={"action": "get_product_dashboard"})
            raise DatabaseError(f"Failed to get product dashboard: {str(e)}")

