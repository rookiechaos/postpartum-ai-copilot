"""
Two-Factor Authentication Service - 2FA management
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import update
import secrets
import pyotp
import qrcode
import io
import base64
from models.database import TwoFactorAuthDB
from services.logging_service import logger
from exceptions import DatabaseError, ValidationError


class TwoFactorAuthService:
    """Service for two-factor authentication"""
    
    def setup_2fa(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Setup 2FA for a user
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            2FA setup data including QR code
        """
        try:
            # Check if 2FA already exists
            existing = db.query(TwoFactorAuthDB).filter(
                TwoFactorAuthDB.user_id == user_id
            ).first()
            if existing and existing.is_enabled:
                raise ValidationError("Disable the current authenticator before setting up another")
            
            # Generate secret key
            secret = pyotp.random_base32()
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
            
            if existing:
                existing.secret_key = secret
                existing.backup_codes = backup_codes
                existing.updated_at = datetime.utcnow()
            else:
                existing = TwoFactorAuthDB(
                    user_id=user_id,
                    secret_key=secret,
                    backup_codes=backup_codes,
                    is_enabled=False
                )
                db.add(existing)
            
            db.commit()
            db.refresh(existing)
            
            # Generate QR code
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user_id,
                issuer_name="Postpartum AI Copilot"
            )
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "secret": secret,
                "backup_codes": backup_codes,
                "qr_code": f"data:image/png;base64,{qr_code_data}",
                "setup_uri": totp_uri
            }
        except Exception as e:
            db.rollback()
            if isinstance(e, ValidationError):
                raise
            logger.log_error(e, context={"action": "setup_2fa", "user_id": user_id})
            raise DatabaseError(f"Failed to setup 2FA: {str(e)}")
    
    def verify_2fa(
        self,
        user_id: str,
        token: str,
        db: Session
    ) -> bool:
        """
        Verify 2FA token
        
        Args:
            user_id: User ID
            token: TOTP token
            db: Database session
        
        Returns:
            True if token is valid
        """
        try:
            two_fa = db.query(TwoFactorAuthDB).filter(
                TwoFactorAuthDB.user_id == user_id,
                TwoFactorAuthDB.is_enabled == True
            ).with_for_update().first()
            
            if not two_fa or not two_fa.secret_key:
                return False
            
            # Verify TOTP token
            totp = pyotp.TOTP(two_fa.secret_key)
            if totp.verify(token, valid_window=1):
                return True
            
            # Check backup codes
            if two_fa.backup_codes and token in two_fa.backup_codes:
                # A write lock also works on SQLite, where FOR UPDATE is ignored.
                # Refresh under that lock so concurrent sessions cannot consume
                # the same code from stale JSON lists.
                locked = db.execute(
                    update(TwoFactorAuthDB).where(
                        TwoFactorAuthDB.id == two_fa.id,
                        TwoFactorAuthDB.is_enabled == True,
                        TwoFactorAuthDB.secret_key == two_fa.secret_key,
                    ).values(updated_at=TwoFactorAuthDB.updated_at)
                    .execution_options(synchronize_session=False)
                )
                if locked.rowcount != 1:
                    db.rollback()
                    return False
                db.refresh(two_fa)
                if token not in (two_fa.backup_codes or []):
                    db.rollback()
                    return False
                two_fa.backup_codes = [code for code in two_fa.backup_codes if code != token]
                db.commit()
                return True
            
            return False
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "verify_2fa", "user_id": user_id})
            return False
    
    def enable_2fa(
        self,
        user_id: str,
        verification_token: str,
        db: Session
    ) -> bool:
        """
        Enable 2FA after verification
        
        Args:
            user_id: User ID
            verification_token: Token to verify setup
            db: Database session
        
        Returns:
            True if enabled successfully
        """
        try:
            two_fa = db.query(TwoFactorAuthDB).filter(
                TwoFactorAuthDB.user_id == user_id
            ).first()
            
            if not two_fa or not two_fa.secret_key:
                raise ValidationError("2FA not set up. Please set it up first.")
            
            # Verify token
            totp = pyotp.TOTP(two_fa.secret_key)
            if not totp.verify(verification_token, valid_window=1):
                raise ValidationError("Invalid verification token")
            
            two_fa.is_enabled = True
            two_fa.updated_at = datetime.utcnow()
            db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            if isinstance(e, ValidationError):
                raise
            logger.log_error(e, context={"action": "enable_2fa", "user_id": user_id})
            raise DatabaseError(f"Failed to enable 2FA: {str(e)}")
    
    def disable_2fa(
        self,
        user_id: str,
        db: Session
    ) -> bool:
        """Disable 2FA for a user"""
        try:
            two_fa = db.query(TwoFactorAuthDB).filter(
                TwoFactorAuthDB.user_id == user_id
            ).first()
            
            if two_fa:
                two_fa.is_enabled = False
                two_fa.updated_at = datetime.utcnow()
                db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "disable_2fa", "user_id": user_id})
            raise DatabaseError(f"Failed to disable 2FA: {str(e)}")
    
    def get_2fa_status(
        self,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Get 2FA status for a user"""
        try:
            two_fa = db.query(TwoFactorAuthDB).filter(
                TwoFactorAuthDB.user_id == user_id
            ).first()
            
            if not two_fa:
                return {
                    "is_enabled": False,
                    "is_setup": False,
                    "has_backup_codes": False
                }
            
            return {
                "is_enabled": two_fa.is_enabled,
                "is_setup": two_fa.secret_key is not None,
                "has_backup_codes": bool(two_fa.backup_codes and len(two_fa.backup_codes) > 0),
                "backup_codes_count": len(two_fa.backup_codes) if two_fa.backup_codes else 0
            }
        except Exception as e:
            logger.log_error(e, context={"action": "get_2fa_status", "user_id": user_id})
            raise DatabaseError("Unable to check two-factor authentication") from e

