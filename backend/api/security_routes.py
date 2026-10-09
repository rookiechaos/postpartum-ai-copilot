"""
Security Routes - 2FA, login history, device management
"""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import DatabaseError, ValidationError, NotFoundError

router = APIRouter(prefix="/api/security", tags=["security"])
container = get_container()


class Enable2FARequest(BaseModel):
    """Enable 2FA request"""
    verification_token: str = Field(..., description="TOTP token to verify setup")


class Verify2FARequest(BaseModel):
    """Verify 2FA token request"""
    token: str = Field(..., description="TOTP token or backup code")


@router.post("/2fa/setup")
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup 2FA for current user"""
    try:
        two_fa_service = container.get("two_factor_auth_service")
        setup_data = two_fa_service.setup_2fa(
            user_id=current_user.user_id,
            db=db
        )
        return {"setup": setup_data, "message": "2FA setup completed. Scan QR code with authenticator app."}
    except (ValidationError, DatabaseError):
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to setup 2FA: {str(e)}")


@router.post("/2fa/enable")
async def enable_2fa(
    request: Enable2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA after verification"""
    try:
        two_fa_service = container.get("two_factor_auth_service")
        success = two_fa_service.enable_2fa(
            user_id=current_user.user_id,
            verification_token=request.verification_token,
            db=db
        )
        return {"enabled": success, "message": "2FA enabled successfully"}
    except (ValidationError, DatabaseError):
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to enable 2FA: {str(e)}")


@router.post("/2fa/disable")
async def disable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA for current user"""
    try:
        two_fa_service = container.get("two_factor_auth_service")
        success = two_fa_service.disable_2fa(
            user_id=current_user.user_id,
            db=db
        )
        return {"disabled": success, "message": "2FA disabled successfully"}
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to disable 2FA: {str(e)}")


@router.get("/2fa/status")
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get 2FA status for current user"""
    try:
        two_fa_service = container.get("two_factor_auth_service")
        status = two_fa_service.get_2fa_status(
            user_id=current_user.user_id,
            db=db
        )
        return {"status": status}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get 2FA status: {str(e)}")


@router.post("/2fa/verify")
async def verify_2fa(
    request: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify 2FA token"""
    try:
        two_fa_service = container.get("two_factor_auth_service")
        is_valid = two_fa_service.verify_2fa(
            user_id=current_user.user_id,
            token=request.token,
            db=db
        )
        return {"valid": is_valid}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to verify 2FA: {str(e)}")


# Device Management
@router.get("/devices")
async def get_devices(
    active_only: bool = Query(True, description="Return only active devices"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all devices for current user"""
    try:
        device_service = container.get("device_service")
        devices = device_service.get_user_devices(
            user_id=current_user.user_id,
            db=db,
            active_only=active_only
        )
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get devices: {str(e)}")


@router.post("/devices/register")
async def register_device(
    request: Request,
    device_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register current device"""
    try:
        device_service = container.get("device_service")
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None
        
        device = device_service.register_device(
            user_id=current_user.user_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
            db=db
        )
        return {"device": device, "message": "Device registered successfully"}
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to register device: {str(e)}")


@router.delete("/devices/{device_id}")
async def remove_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a device"""
    try:
        device_service = container.get("device_service")
        success = device_service.remove_device(
            user_id=current_user.user_id,
            device_id=device_id,
            db=db
        )
        return {"removed": success, "message": "Device removed successfully"}
    except NotFoundError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to remove device: {str(e)}")


@router.post("/devices/{device_id}/trust")
async def trust_device(
    device_id: str,
    is_trusted: bool = Query(True, description="Trust status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark device as trusted or untrusted"""
    try:
        device_service = container.get("device_service")
        success = device_service.trust_device(
            user_id=current_user.user_id,
            device_id=device_id,
            is_trusted=is_trusted,
            db=db
        )
        return {"trusted": is_trusted, "message": f"Device {'trusted' if is_trusted else 'untrusted'} successfully"}
    except NotFoundError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to update device trust: {str(e)}")


# Login History
@router.get("/login-history")
async def get_login_history(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of entries"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get login history for current user"""
    try:
        device_service = container.get("device_service")
        history = device_service.get_login_history(
            user_id=current_user.user_id,
            limit=limit,
            db=db
        )
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get login history: {str(e)}")

