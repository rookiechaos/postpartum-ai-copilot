"""
Device Service - Device management and tracking
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
import secrets
import hashlib
from models.database import DeviceDB, LoginHistoryDB
from services.logging_service import logger
from exceptions import DatabaseError, NotFoundError


class DeviceService:
    """Service for device management"""
    
    def register_device(
        self,
        user_id: str,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Register a new device
        
        Args:
            user_id: User ID
            device_name: User-friendly device name
            device_type: Device type (mobile, desktop, tablet)
            user_agent: User agent string
            ip_address: IP address
            db: Database session
        
        Returns:
            Device registration data
        """
        try:
            # Generate device ID from user agent and IP
            device_id = hashlib.sha256(
                f"{user_id}:{user_agent}:{ip_address}".encode()
            ).hexdigest()[:16]
            
            # Check if device already exists
            existing = db.query(DeviceDB).filter(
                DeviceDB.device_id == device_id,
                DeviceDB.user_id == user_id
            ).first()
            
            if existing:
                # Update last used
                existing.last_used = datetime.utcnow()
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                
                return {
                    "device_id": existing.device_id,
                    "device_name": existing.device_name,
                    "device_type": existing.device_type,
                    "is_trusted": existing.is_trusted,
                    "last_used": existing.last_used.isoformat() if existing.last_used else None
                }
            
            # Create new device
            device = DeviceDB(
                user_id=user_id,
                device_id=device_id,
                device_name=device_name or f"Device {device_id[:8]}",
                device_type=device_type or self._detect_device_type(user_agent),
                user_agent=user_agent,
                ip_address=ip_address,
                is_active=True,
                is_trusted=False
            )
            db.add(device)
            db.commit()
            db.refresh(device)
            
            return {
                "device_id": device.device_id,
                "device_name": device.device_name,
                "device_type": device.device_type,
                "is_trusted": device.is_trusted,
                "last_used": device.last_used.isoformat() if device.last_used else None
            }
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "register_device", "user_id": user_id})
            raise DatabaseError(f"Failed to register device: {str(e)}")
    
    def _detect_device_type(self, user_agent: Optional[str]) -> str:
        """Detect device type from user agent"""
        if not user_agent:
            return "unknown"
        
        user_agent_lower = user_agent.lower()
        if "mobile" in user_agent_lower or "android" in user_agent_lower or "iphone" in user_agent_lower:
            return "mobile"
        elif "tablet" in user_agent_lower or "ipad" in user_agent_lower:
            return "tablet"
        else:
            return "desktop"
    
    def get_user_devices(
        self,
        user_id: str,
        db: Session,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all devices for a user"""
        try:
            query = db.query(DeviceDB).filter(DeviceDB.user_id == user_id)
            
            if active_only:
                query = query.filter(DeviceDB.is_active == True)
            
            devices = query.order_by(desc(DeviceDB.last_used)).all()
            
            return [{
                "device_id": d.device_id,
                "device_name": d.device_name,
                "device_type": d.device_type,
                "user_agent": d.user_agent,
                "ip_address": d.ip_address,
                "is_trusted": d.is_trusted,
                "is_active": d.is_active,
                "last_used": d.last_used.isoformat() if d.last_used else None,
                "created_at": d.created_at.isoformat() if d.created_at else None
            } for d in devices]
        except Exception as e:
            logger.log_error(e, context={"action": "get_user_devices", "user_id": user_id})
            return []
    
    def remove_device(
        self,
        user_id: str,
        device_id: str,
        db: Session
    ) -> bool:
        """Remove a device"""
        try:
            device = db.query(DeviceDB).filter(
                DeviceDB.device_id == device_id,
                DeviceDB.user_id == user_id
            ).first()
            
            if not device:
                raise NotFoundError("Device not found")
            
            device.is_active = False
            db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            if isinstance(e, NotFoundError):
                raise
            logger.log_error(e, context={"action": "remove_device"})
            raise DatabaseError(f"Failed to remove device: {str(e)}")
    
    def trust_device(
        self,
        user_id: str,
        device_id: str,
        is_trusted: bool,
        db: Session
    ) -> bool:
        """Mark device as trusted or untrusted"""
        try:
            device = db.query(DeviceDB).filter(
                DeviceDB.device_id == device_id,
                DeviceDB.user_id == user_id
            ).first()
            
            if not device:
                raise NotFoundError("Device not found")
            
            device.is_trusted = is_trusted
            db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            if isinstance(e, NotFoundError):
                raise
            logger.log_error(e, context={"action": "trust_device"})
            raise DatabaseError(f"Failed to update device trust: {str(e)}")
    
    def log_login(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
        login_method: str = "password",
        success: bool = True,
        failure_reason: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Log a login attempt
        
        Args:
            user_id: User ID
            ip_address: IP address
            user_agent: User agent string
            device_info: Device information
            login_method: Login method used
            success: Whether login was successful
            failure_reason: Reason for failure if unsuccessful
            db: Database session
        
        Returns:
            Login history entry
        """
        try:
            login_history = LoginHistoryDB(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info,
                login_method=login_method,
                success=success,
                failure_reason=failure_reason
            )
            db.add(login_history)
            db.commit()
            db.refresh(login_history)
            
            return {
                "id": login_history.id,
                "user_id": login_history.user_id,
                "ip_address": login_history.ip_address,
                "login_method": login_history.login_method,
                "success": login_history.success,
                "created_at": login_history.created_at.isoformat() if login_history.created_at else None
            }
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "log_login", "user_id": user_id})
            raise DatabaseError(f"Failed to log login: {str(e)}")
    
    def get_login_history(
        self,
        user_id: str,
        limit: int = 50,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Get login history for a user"""
        try:
            history = db.query(LoginHistoryDB).filter(
                LoginHistoryDB.user_id == user_id
            ).order_by(desc(LoginHistoryDB.created_at)).limit(limit).all()
            
            return [{
                "id": h.id,
                "ip_address": h.ip_address,
                "user_agent": h.user_agent,
                "device_info": h.device_info,
                "login_method": h.login_method,
                "success": h.success,
                "failure_reason": h.failure_reason,
                "created_at": h.created_at.isoformat() if h.created_at else None
            } for h in history]
        except Exception as e:
            logger.log_error(e, context={"action": "get_login_history", "user_id": user_id})
            return []

