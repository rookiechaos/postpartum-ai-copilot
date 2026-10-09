"""
Data Export Routes - API endpoints for data export (GDPR compliant)
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from exceptions import DatabaseError, ServiceUnavailableError
import json
import io

router = APIRouter()
container = get_container()


@router.get("/json")
async def export_data_json(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export user data as JSON (GDPR compliant)
    
    Returns all user data in JSON format for download
    """
    try:
        export_service = container.get("data_export_service")
        data = export_service.export_user_data_json(current_user.user_id, db)
        
        json_string = json.dumps(data, indent=2, default=str)
        
        return Response(
            content=json_string,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=user_data_{current_user.user_id}_{datetime.utcnow().strftime('%Y%m%d')}.json"
            }
        )
    except Exception as e:
        raise DatabaseError(
            f"Failed to export data: {str(e)}",
            details={"user_id": current_user.user_id, "format": "json", "original_error": str(e)}
        )


@router.get("/csv")
async def export_data_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export user data as CSV
    
    Returns all user data in CSV format for download
    """
    try:
        export_service = container.get("data_export_service")
        csv_string = export_service.export_user_data_csv(current_user.user_id, db)
        
        return Response(
            content=csv_string,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=user_data_{current_user.user_id}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            }
        )
    except Exception as e:
        raise DatabaseError(
            f"Failed to export data: {str(e)}",
            details={"user_id": current_user.user_id, "format": "csv", "original_error": str(e)}
        )


@router.get("/pdf")
async def export_data_pdf(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export user data as PDF
    
    Returns all user data in PDF format for download
    """
    try:
        export_service = container.get("data_export_service")
        pdf_bytes = export_service.export_user_data_pdf(current_user.user_id, db)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=user_data_{current_user.user_id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
            }
        )
    except ImportError as e:
        raise ServiceUnavailableError(
            "PDF export requires reportlab. Install with: pip install reportlab",
            details={"missing_dependency": "reportlab", "user_id": current_user.user_id}
        )
    except Exception as e:
        raise DatabaseError(
            f"Failed to export data: {str(e)}",
            details={"user_id": current_user.user_id, "format": "pdf", "original_error": str(e)}
        )
