"""
Referral Service - User referral and invitation system
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import uuid
import secrets
from models.database import UserDB
from services.logging_service import logger
from exceptions import DatabaseError, NotFoundError, ValidationError


class ReferralService:
    """Service for managing user referrals"""
    
    def generate_referral_code(
        self,
        user_id: str,
        db: Session
    ) -> str:
        """
        Generate a unique referral code for a user
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            Referral code
        """
        try:
            # Generate a unique code
            code = f"REF{secrets.token_hex(4).upper()}"
            
            # Store in user metadata or separate table
            # For now, we'll use a simple approach with user_id hash
            # In production, you'd want a ReferralCodeDB table
            referral_code = f"{user_id[:8]}-{code}"
            
            return referral_code
        except Exception as e:
            logger.log_error(e, context={"action": "generate_referral_code", "user_id": user_id})
            raise DatabaseError(f"Failed to generate referral code: {str(e)}")
    
    def track_referral(
        self,
        referrer_user_id: str,
        referred_user_id: str,
        referral_code: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Track a referral
        
        Args:
            referrer_user_id: User who made the referral
            referred_user_id: User who was referred
            referral_code: Optional referral code
            db: Database session
        
        Returns:
            Referral tracking data
        """
        try:
            # In production, you'd have a ReferralDB table
            # For now, we'll track via events or metadata
            referral_id = f"ref_{uuid.uuid4().hex[:12]}"
            
            # Log the referral
            logger.log_user_action(
                user_id=referrer_user_id,
                action="referral_made",
                details={
                    "referral_id": referral_id,
                    "referred_user_id": referred_user_id,
                    "referral_code": referral_code
                }
            )
            
            return {
                "referral_id": referral_id,
                "referrer_user_id": referrer_user_id,
                "referred_user_id": referred_user_id,
                "referral_code": referral_code,
                "created_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.log_error(e, context={"action": "track_referral"})
            raise DatabaseError(f"Failed to track referral: {str(e)}")
    
    def get_referral_stats(
        self,
        user_id: str,
        days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get referral statistics for a user
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            db: Database session
        
        Returns:
            Referral statistics
        """
        try:
            # In production, query ReferralDB table
            # For now, return placeholder stats
            return {
                "total_referrals": 0,
                "active_referrals": 0,
                "converted_referrals": 0,
                "referral_code": self.generate_referral_code(user_id, db),
                "period_days": days
            }
        except Exception as e:
            logger.log_error(e, context={"action": "get_referral_stats", "user_id": user_id})
            return {
                "total_referrals": 0,
                "active_referrals": 0,
                "converted_referrals": 0,
                "referral_code": None,
                "period_days": days
            }
    
    def validate_referral_code(
        self,
        referral_code: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a referral code
        
        Args:
            referral_code: Referral code to validate
            db: Database session
        
        Returns:
            Referral code info if valid, None otherwise
        """
        try:
            # In production, query ReferralCodeDB table
            # For now, simple validation
            if referral_code and len(referral_code) > 5:
                # Extract user_id from code (if using format: user_id-code)
                parts = referral_code.split("-")
                if len(parts) >= 2:
                    user_id_prefix = parts[0]
                    # Find user by prefix (simplified - in production use proper lookup)
                    return {
                        "valid": True,
                        "referral_code": referral_code,
                        "message": "Referral code is valid"
                    }
            
            return None
        except Exception as e:
            logger.log_error(e, context={"action": "validate_referral_code"})
            return None

