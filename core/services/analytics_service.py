"""
Analytics Service - Usage statistics and analysis
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from collections import defaultdict

from models.database import SessionLocal, TaskDB, TrackingEntryDB
from services.logging_service import logger
from exceptions import DatabaseError


class AnalyticsService:
    """Service for usage analytics and statistics"""
    
    def get_user_usage_stats(
        self,
        user_id: str,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a user
        
        Returns:
        - Total interactions
        - Tasks created/completed/failed
        - Tracking entries
        - Most used features
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Task statistics
            tasks = db.query(TaskDB).filter(
                TaskDB.user_id == user_id,
                TaskDB.created_at >= cutoff_date
            ).all()
            
            task_stats = {
                "total": len(tasks),
                "completed": sum(1 for t in tasks if t.status == "completed"),
                "failed": sum(1 for t in tasks if t.status == "failed"),
                "pending": sum(1 for t in tasks if t.status == "pending"),
                "processing": sum(1 for t in tasks if t.status == "processing")
            }
            
            # Task types
            task_types = defaultdict(int)
            for task in tasks:
                task_types[task.task_type] += 1
            
            # Tracking entries
            tracking_entries = db.query(TrackingEntryDB).filter(
                TrackingEntryDB.user_id == user_id,
                TrackingEntryDB.timestamp >= cutoff_date
            ).all()
            
            tracking_stats = {
                "total": len(tracking_entries),
                "by_type": defaultdict(int)
            }
            
            for entry in tracking_entries:
                tracking_stats["by_type"][entry.entry_type] += 1
            
            return {
                "user_id": user_id,
                "period_days": days,
                "tasks": task_stats,
                "task_types": dict(task_types),
                "tracking": tracking_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.log_error(e, context={"user_id": user_id})
            raise DatabaseError(f"Failed to get user usage stats: {str(e)}")
    
    def get_system_stats(
        self,
        db: Session,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get system-wide statistics
        
        Returns:
        - Total users
        - Total tasks
        - Task success rate
        - Average response time
        - Most active users
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Task statistics
            tasks = db.query(TaskDB).filter(
                TaskDB.created_at >= cutoff_date
            ).all()
            
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.status == "completed")
            success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Calculate average processing time
            completed_with_times = [
                t for t in tasks
                if t.status == "completed" and t.started_at and t.completed_at
            ]
            
            avg_processing_time = 0
            if completed_with_times:
                processing_times = [
                    (t.completed_at - t.started_at).total_seconds()
                    for t in completed_with_times
                ]
                avg_processing_time = sum(processing_times) / len(processing_times)
            
            # User activity
            user_activity = defaultdict(int)
            for task in tasks:
                user_activity[task.user_id] += 1
            
            top_users = sorted(
                user_activity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Task type distribution
            task_type_dist = defaultdict(int)
            for task in tasks:
                task_type_dist[task.task_type] += 1
            
            return {
                "period_days": days,
                "tasks": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "failed": sum(1 for t in tasks if t.status == "failed"),
                    "success_rate_percent": round(success_rate, 2),
                    "avg_processing_time_seconds": round(avg_processing_time, 2)
                },
                "task_types": dict(task_type_dist),
                "top_users": [{"user_id": uid, "task_count": count} for uid, count in top_users],
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.log_error(e)
            raise
    
    def get_task_performance_stats(
        self,
        db: Session,
        task_type: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get task performance statistics
        
        Args:
            db: Database session
            task_type: Filter by task type (optional)
            days: Number of days to analyze
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = db.query(TaskDB).filter(
                TaskDB.created_at >= cutoff_date
            )
            
            if task_type:
                query = query.filter(TaskDB.task_type == task_type)
            
            tasks = query.all()
            
            # Performance metrics
            completed_tasks = [
                t for t in tasks
                if t.status == "completed" and t.started_at and t.completed_at
            ]
            
            if not completed_tasks:
                return {
                    "task_type": task_type or "all",
                    "period_days": days,
                    "total_tasks": len(tasks),
                    "completed_tasks": 0,
                    "avg_processing_time_seconds": 0,
                    "p95_processing_time_seconds": 0,
                    "p99_processing_time_seconds": 0
                }
            
            processing_times = sorted([
                (t.completed_at - t.started_at).total_seconds()
                for t in completed_tasks
            ])
            
            avg_time = sum(processing_times) / len(processing_times)
            p95_index = int(len(processing_times) * 0.95)
            p99_index = int(len(processing_times) * 0.99)
            
            return {
                "task_type": task_type or "all",
                "period_days": days,
                "total_tasks": len(tasks),
                "completed_tasks": len(completed_tasks),
                "avg_processing_time_seconds": round(avg_time, 2),
                "p95_processing_time_seconds": round(processing_times[p95_index] if p95_index < len(processing_times) else 0, 2),
                "p99_processing_time_seconds": round(processing_times[p99_index] if p99_index < len(processing_times) else 0, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.log_error(e)
            raise


# Global analytics service instance
_analytics_service = None


def get_analytics_service() -> AnalyticsService:
    """Get global analytics service instance"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service

