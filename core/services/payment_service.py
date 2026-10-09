"""
Payment Service - Subscription and payment management
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.database import SubscriptionDB, UserDB
from services.logging_service import logger
from exceptions import ValidationError, NotFoundError


class PaymentService:
    """Service for managing subscriptions and payments"""
    
    def __init__(self):
        # Payment provider configuration
        self.providers = {
            "stripe": {
                "enabled": False,  # Set to True when Stripe keys are configured
                "api_key": None  # Load from settings
            },
            "paypal": {
                "enabled": False,  # Set to True when PayPal is configured
                "client_id": None
            }
        }
    
    def create_subscription(
        self,
        user_id: str,
        plan: str,
        payment_provider: str,
        payment_provider_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create a subscription
        
        Args:
            user_id: User ID
            plan: Plan name (free, premium, enterprise)
            payment_provider: Payment provider (stripe, paypal)
            payment_provider_id: Subscription ID from provider
            db: Database session
        
        Returns:
            Created subscription dictionary
        """
        try:
            # Validate plan
            valid_plans = ["free", "premium", "enterprise"]
            if plan not in valid_plans:
                raise ValidationError(f"Invalid plan: {plan}. Must be one of {valid_plans}")
            
            # Check if user already has an active subscription
            existing = db.query(SubscriptionDB).filter(
                SubscriptionDB.user_id == user_id,
                SubscriptionDB.status == "active"
            ).first()
            
            if existing:
                # Update existing subscription
                existing.plan = plan
                existing.payment_provider = payment_provider
                if payment_provider_id:
                    existing.payment_provider_id = payment_provider_id
                existing.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing)
                return self._subscription_to_dict(existing)
            
            # Create new subscription
            now = datetime.utcnow()
            subscription = SubscriptionDB(
                user_id=user_id,
                plan=plan,
                status="active",
                payment_provider=payment_provider,
                payment_provider_id=payment_provider_id,
                current_period_start=now,
                current_period_end=now + timedelta(days=30)  # Default 30 days
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            logger.log_info(f"Subscription created: {plan} for user {user_id}")
            
            return self._subscription_to_dict(subscription)
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "create_subscription", "user_id": user_id})
            raise
    
    def get_user_subscription(
        self,
        user_id: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Get user's current subscription"""
        try:
            subscription = db.query(SubscriptionDB).filter(
                SubscriptionDB.user_id == user_id,
                SubscriptionDB.status == "active"
            ).first()
            
            if subscription:
                return self._subscription_to_dict(subscription)
            return None
        except Exception as e:
            logger.log_error(e, context={"action": "get_user_subscription", "user_id": user_id})
            return None
    
    def cancel_subscription(
        self,
        user_id: str,
        cancel_at_period_end: bool = True,
        db: Session = None
    ) -> bool:
        """
        Cancel a subscription
        
        Args:
            user_id: User ID
            cancel_at_period_end: Whether to cancel at period end or immediately
            db: Database session
        
        Returns:
            True if cancelled successfully
        """
        try:
            subscription = db.query(SubscriptionDB).filter(
                SubscriptionDB.user_id == user_id,
                SubscriptionDB.status == "active"
            ).first()
            
            if not subscription:
                raise NotFoundError("No active subscription found")
            
            if cancel_at_period_end:
                subscription.cancel_at_period_end = True
                subscription.status = "active"  # Keep active until period end
            else:
                subscription.status = "cancelled"
                subscription.cancelled_at = datetime.utcnow()
            
            subscription.updated_at = datetime.utcnow()
            db.commit()
            
            logger.log_info(f"Subscription cancelled for user {user_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "cancel_subscription", "user_id": user_id})
            raise
    
    def update_subscription_status(
        self,
        payment_provider_id: str,
        status: str,
        db: Session
    ) -> bool:
        """Update subscription status from webhook"""
        try:
            subscription = db.query(SubscriptionDB).filter(
                SubscriptionDB.payment_provider_id == payment_provider_id
            ).first()
            
            if not subscription:
                return False
            
            subscription.status = status
            if status == "cancelled":
                subscription.cancelled_at = datetime.utcnow()
            
            subscription.updated_at = datetime.utcnow()
            db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "update_subscription_status"})
            return False
    
    def check_subscription_access(
        self,
        user_id: str,
        feature: str,
        db: Session
    ) -> bool:
        """
        Check if user has access to a feature based on subscription
        
        Args:
            user_id: User ID
            feature: Feature name to check
            db: Database session
        
        Returns:
            True if user has access
        """
        subscription = self.get_user_subscription(user_id, db)
        
        if not subscription:
            # Default to free plan
            plan = "free"
        else:
            plan = subscription["plan"]
        
        # Feature access matrix
        feature_access = {
            "free": {
                "basic_chat": True,
                "tracking": True,
                "basic_notifications": True,
                "data_export": False,
                "advanced_analytics": False,
                "family_sharing": False,
                "voice_interaction": False,
                "priority_support": False
            },
            "premium": {
                "basic_chat": True,
                "tracking": True,
                "basic_notifications": True,
                "data_export": True,
                "advanced_analytics": True,
                "family_sharing": True,
                "voice_interaction": True,
                "priority_support": False
            },
            "enterprise": {
                "basic_chat": True,
                "tracking": True,
                "basic_notifications": True,
                "data_export": True,
                "advanced_analytics": True,
                "family_sharing": True,
                "voice_interaction": True,
                "priority_support": True
            }
        }
        
        return feature_access.get(plan, {}).get(feature, False)
    
    def _subscription_to_dict(self, subscription: SubscriptionDB) -> Dict[str, Any]:
        """Convert database subscription to dictionary"""
        return {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "plan": subscription.plan,
            "status": subscription.status,
            "payment_provider": subscription.payment_provider,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
            "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
            "created_at": subscription.created_at.isoformat() if subscription.created_at else None,
            "updated_at": subscription.updated_at.isoformat() if subscription.updated_at else None
        }

