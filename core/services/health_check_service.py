"""
Health Check Service - Comprehensive system health monitoring
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_engine, SessionLocal
from services.logging_service import logger
from config.settings import get_settings


class HealthCheckService:
    """Service for comprehensive health checks"""
    
    def __init__(self):
        try:
            self.engine = get_engine()
        except:
            self.engine = None
    
    def check_database(self, db: Session) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            # Simple query to check connectivity
            result = db.execute(text("SELECT 1"))
            result.fetchone()
            
            # Check database type
            settings = get_settings()
            db_url = settings.database_url
            db_type = "sqlite" if "sqlite" in db_url else "postgresql"
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "healthy",
                "type": db_type,
                "response_time_ms": round(response_time, 2),
                "connected": True
            }
        except Exception as e:
            logger.log_error(e, context={"check": "database"})
            return {
                "status": "unhealthy",
                "error": "Database health check failed",
                "connected": False
            }
    
    def check_ai_provider(self) -> Dict[str, Any]:
        """Check AI provider status"""
        try:
            settings = get_settings()
            provider = settings.ai_provider.lower()
            
            # Check if API key is set
            api_key = settings.get_ai_api_key()
            
            if not api_key:
                return {
                    "status": "not_configured",
                    "provider": provider,
                    "message": "API key not set"
                }
            
            return {
                "status": "configured",
                "provider": provider,
                "api_key_set": True
            }
        except Exception as e:
            logger.log_error(e, context={"check": "ai_provider"})
            return {
                "status": "error",
                "error": "AI provider health check failed"
            }
    
    def check_task_queue(self, db: Session) -> Dict[str, Any]:
        """Check task queue status"""
        try:
            from services.task_queue import TaskQueue
            from models.database import TaskDB
            from datetime import timedelta
            
            queue = TaskQueue()
            
            # Get pending tasks count
            pending_tasks = queue.get_pending_tasks(db, limit=100)
            pending_count = len(pending_tasks)
            
            # Get recent tasks stats (last hour)
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_tasks = db.query(TaskDB).filter(
                TaskDB.created_at >= one_hour_ago
            ).all()
            
            completed = sum(1 for t in recent_tasks if t.status == "completed")
            failed = sum(1 for t in recent_tasks if t.status == "failed")
            processing = sum(1 for t in recent_tasks if t.status == "processing")
            
            return {
                "status": "healthy",
                "pending_tasks": pending_count,
                "recent_stats": {
                    "total": len(recent_tasks),
                    "completed": completed,
                    "failed": failed,
                    "processing": processing
                }
            }
        except Exception as e:
            logger.log_error(e, context={"check": "task_queue"})
            return {
                "status": "error",
                "error": "Task queue health check failed"
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy",
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "status": "healthy" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "critical"
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent": memory.percent,
                    "status": "healthy" if memory.percent < 80 else "warning" if memory.percent < 95 else "critical"
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 2),
                    "status": "healthy" if (disk.used / disk.total) < 0.8 else "warning" if (disk.used / disk.total) < 0.95 else "critical"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except ImportError:
            return {
                "status": "not_available",
                "message": "psutil not installed"
            }
        except Exception as e:
            logger.log_error(e, context={"check": "system_resources"})
            return {
                "status": "error",
                "error": "System resources health check failed"
            }
    
    def get_comprehensive_health(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive health status of all services"""
        checks = {
            "database": self.check_database(db),
            "ai_provider": self.check_ai_provider(),
            "task_queue": self.check_task_queue(db),
            "system_resources": self.check_system_resources()
        }
        
        # Determine overall status
        all_healthy = all(
            check.get("status") in ["healthy", "configured", "not_configured", "not_available"]
            for check in checks.values()
        )
        
        # Critical services must be healthy
        critical_healthy = checks["database"].get("status") == "healthy"
        
        overall_status = "healthy" if (all_healthy and critical_healthy) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
            "version": "2.0.0"
        }


# Global health check service instance
_health_check_service: Optional[HealthCheckService] = None


def get_health_check_service() -> HealthCheckService:
    """Get global health check service instance"""
    global _health_check_service
    if _health_check_service is None:
        _health_check_service = HealthCheckService()
    return _health_check_service

