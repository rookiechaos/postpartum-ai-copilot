"""
Product Analytics Routes - Product metrics and analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user, get_optional_user
from middleware.admin import require_admin
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger

router = APIRouter()
container = get_container()


class TrackEventRequest(BaseModel):
    event_type: str = Field(..., description="Event type: page_view, click, action, conversion")
    event_name: str = Field(..., description="Event name")
    event_category: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    page_url: Optional[str] = None


@router.post("/events")
async def track_event(
    event: TrackEventRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Track a user event"""
    try:
        analytics_service = container.get("product_analytics_service")
        user_id = current_user.user_id if current_user else None
        
        result = analytics_service.track_event(
            user_id=user_id,
            event_type=event.event_type,
            event_name=event.event_name,
            event_category=event.event_category,
            event_data=event.event_data,
            properties=event.properties,
            session_id=event.session_id,
            page_url=event.page_url,
            db=db
        )
        
        return result
    except Exception as e:
        logger.log_error(e, context={"action": "track_event"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track event: {str(e)}"
        )


@router.get("/dashboard")
async def get_product_dashboard(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive product dashboard (admin only)"""
    try:
        analytics_service = container.get("product_analytics_service")
        dashboard = analytics_service.get_product_dashboard(days=days, db=db)
        return dashboard
    except Exception as e:
        logger.log_error(e, context={"action": "get_product_dashboard"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )


@router.get("/metrics/dau")
async def get_dau(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Daily Active Users"""
    try:
        analytics_service = container.get("product_analytics_service")
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        dau = analytics_service.get_dau(date=target_date, db=db)
        return {"dau": dau, "date": date or datetime.utcnow().date().isoformat()}
    except Exception as e:
        logger.log_error(e, context={"action": "get_dau"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DAU: {str(e)}"
        )


@router.get("/metrics/mau")
async def get_mau(
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Monthly Active Users"""
    try:
        analytics_service = container.get("product_analytics_service")
        target_month = None
        if month:
            try:
                target_month = datetime.strptime(f"{month}-01", "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
        mau = analytics_service.get_mau(month=target_month, db=db)
        return {"mau": mau, "month": month or datetime.utcnow().strftime("%Y-%m")}
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(e, context={"action": "get_mau"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get MAU: {str(e)}"
        )


@router.get("/metrics/retention")
async def get_retention(
    cohort_date: str = Query(..., description="Cohort date in YYYY-MM-DD format"),
    days: int = Query(7, ge=1, le=365, description="Days after cohort"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get retention rate for a cohort"""
    try:
        analytics_service = container.get("product_analytics_service")
        try:
            cohort = datetime.strptime(cohort_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        retention = analytics_service.get_retention_rate(cohort, days=days, db=db)
        return {
            "cohort_date": cohort_date,
            "days": days,
            "retention_rate": retention
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(e, context={"action": "get_retention"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get retention: {str(e)}"
        )


@router.get("/metrics/retention-analysis")
async def get_retention_analysis(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive retention analysis (day 1, 7, 14, 30 retention rates)"""
    try:
        analytics_service = container.get("product_analytics_service")
        analysis = analytics_service.get_retention_analysis(days=days, db=db)
        return analysis
    except Exception as e:
        logger.log_error(e, context={"action": "get_retention_analysis"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get retention analysis: {str(e)}"
        )


@router.get("/metrics/conversion-funnel")
async def get_conversion_funnel(
    days: int = Query(7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversion funnel data"""
    try:
        analytics_service = container.get("product_analytics_service")
        funnel = analytics_service.get_conversion_funnel(days=days, db=db)
        return funnel
    except Exception as e:
        logger.log_error(e, context={"action": "get_conversion_funnel"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversion funnel: {str(e)}"
        )


@router.get("/metrics/feature-usage")
async def get_feature_usage(
    days: int = Query(7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feature usage statistics"""
    try:
        analytics_service = container.get("product_analytics_service")
        usage = analytics_service.get_feature_usage(days=days, db=db)
        return {"feature_usage": usage, "days": days}
    except Exception as e:
        logger.log_error(e, context={"action": "get_feature_usage"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature usage: {str(e)}"
        )


@router.get("/metrics/user-path/{user_id}")
async def get_user_path(
    user_id: str,
    days: int = Query(7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user path analysis"""
    try:
        # Check authorization
        from middleware.authorization import check_user_authorization
        check_user_authorization(current_user, user_id, "user analytics")
        
        analytics_service = container.get("product_analytics_service")
        path = analytics_service.get_user_path_analysis(user_id, days=days, db=db)
        return {"user_id": user_id, "path": path, "days": days}
    except Exception as e:
        logger.log_error(e, context={"action": "get_user_path"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user path: {str(e)}"
        )


@router.post("/metrics/calculate-daily")
async def calculate_daily_metrics(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Calculate and store daily metrics (admin only)"""
    try:
        analytics_service = container.get("product_analytics_service")
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        metrics = analytics_service.calculate_daily_metrics(date=target_date, db=db)
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.log_error(e, context={"action": "calculate_daily_metrics"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate metrics: {str(e)}"
        )

