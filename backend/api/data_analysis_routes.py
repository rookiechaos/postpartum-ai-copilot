"""
Data Analysis Routes - Advanced data analysis API
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import DatabaseError

router = APIRouter(prefix="/api/analysis", tags=["data-analysis"])
container = get_container()


@router.get("/predict/{entry_type}")
async def predict_trends(
    entry_type: str,
    days: int = Query(30, ge=7, le=365, description="Days of historical data"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Predict future trends based on historical data"""
    try:
        analysis_service = container.get("data_analysis_service")
        prediction = analysis_service.predict_trends(
            user_id=current_user.user_id,
            entry_type=entry_type,
            days=days,
            db=db
        )
        return {"prediction": prediction}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to predict trends: {str(e)}")


@router.get("/compare/{entry_type}")
async def compare_periods(
    entry_type: str,
    period1_days: int = Query(7, ge=1, le=90, description="Days for recent period"),
    period2_days: int = Query(7, ge=1, le=90, description="Days for older period"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare data between two time periods"""
    try:
        analysis_service = container.get("data_analysis_service")
        comparison = analysis_service.compare_periods(
            user_id=current_user.user_id,
            entry_type=entry_type,
            period1_days=period1_days,
            period2_days=period2_days,
            db=db
        )
        return {"comparison": comparison}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to compare periods: {str(e)}")


@router.get("/anomalies/{entry_type}")
async def detect_anomalies(
    entry_type: str,
    days: int = Query(30, ge=7, le=365, description="Days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect anomalies in tracking data"""
    try:
        analysis_service = container.get("data_analysis_service")
        anomalies = analysis_service.detect_anomalies(
            user_id=current_user.user_id,
            entry_type=entry_type,
            days=days,
            db=db
        )
        return {"anomalies": anomalies, "count": len(anomalies)}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to detect anomalies: {str(e)}")


@router.get("/report")
async def generate_report(
    days: int = Query(30, ge=1, le=365, description="Days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate detailed data analysis report"""
    try:
        analysis_service = container.get("data_analysis_service")
        report = analysis_service.generate_detailed_report(
            user_id=current_user.user_id,
            days=days,
            db=db
        )
        return {"report": report}
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to generate report: {str(e)}")

