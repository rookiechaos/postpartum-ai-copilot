"""
Payment Routes - API endpoints for subscriptions and payments
"""

from fastapi import APIRouter, Depends, status, Header, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import ValidationError, NotFoundError, DatabaseError, ConflictError
from utils.webhook_verification import verify_stripe_webhook, verify_paypal_webhook
import json

router = APIRouter()
container = get_container()


class SubscriptionCreate(BaseModel):
    plan: str = Field(..., pattern="^(free|premium|enterprise)$")
    payment_provider: str = Field(..., pattern="^(stripe|paypal)$")
    payment_provider_id: Optional[str] = None


class SubscriptionResponse(BaseModel):
    id: int
    user_id: str
    plan: str
    status: str
    payment_provider: Optional[str]
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool
    cancelled_at: Optional[str]
    trial_end: Optional[str]
    created_at: str
    updated_at: str


@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    subscription: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription"""
    try:
        payment_service = container.get("payment_service")
        created = payment_service.create_subscription(
            user_id=current_user.user_id,
            plan=subscription.plan,
            payment_provider=subscription.payment_provider,
            payment_provider_id=subscription.payment_provider_id,
            db=db
        )
        return SubscriptionResponse(**created)
    except (ValidationError, ConflictError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to create subscription: {str(e)}",
            details={"user_id": current_user.user_id, "plan": subscription.plan, "original_error": str(e)}
        )


@router.get("/subscriptions/me", response_model=Optional[SubscriptionResponse])
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription"""
    try:
        payment_service = container.get("payment_service")
        subscription = payment_service.get_user_subscription(
            user_id=current_user.user_id,
            db=db
        )
        if subscription:
            return SubscriptionResponse(**subscription)
        return None
    except Exception as e:
        raise DatabaseError(
            f"Failed to get subscription: {str(e)}",
            details={"user_id": current_user.user_id, "original_error": str(e)}
        )


@router.post("/subscriptions/cancel")
async def cancel_subscription(
    cancel_at_period_end: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel current subscription"""
    try:
        payment_service = container.get("payment_service")
        success = payment_service.cancel_subscription(
            user_id=current_user.user_id,
            cancel_at_period_end=cancel_at_period_end,
            db=db
        )
        return {"status": "cancelled", "cancel_at_period_end": cancel_at_period_end}
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to cancel subscription: {str(e)}",
            details={"user_id": current_user.user_id, "original_error": str(e)}
        )


@router.get("/subscriptions/check-access")
async def check_feature_access(
    feature: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has access to a feature"""
    try:
        payment_service = container.get("payment_service")
        has_access = payment_service.check_subscription_access(
            user_id=current_user.user_id,
            feature=feature,
            db=db
        )
        return {
            "user_id": current_user.user_id,
            "feature": feature,
            "has_access": has_access
        }
    except Exception as e:
        raise DatabaseError(
            f"Failed to check access: {str(e)}",
            details={"user_id": current_user.user_id, "feature": feature, "original_error": str(e)}
        )


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Handle Stripe webhook events
    
    Args:
        request: FastAPI request object
        stripe_signature: Stripe signature from header
        db: Database session
        
    Returns:
        Status response
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature
        verify_stripe_webhook(
            payload=body,
            signature=stripe_signature
        )
        
        # Parse JSON payload from body bytes
        payload = json.loads(body.decode('utf-8'))
        event_type = payload.get("type")
        data = payload.get("data", {}).get("object", {})
        
        payment_service = container.get("payment_service")
        
        if event_type == "customer.subscription.updated":
            subscription_id = data.get("id")
            status = data.get("status")
            payment_service.update_subscription_status(
                payment_provider_id=subscription_id,
                status=status,
                db=db
            )
        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id")
            payment_service.update_subscription_status(
                payment_provider_id=subscription_id,
                status="cancelled",
                db=db
            )
        
        logger.log_info(f"Stripe webhook processed: {event_type}")
        return {"status": "ok"}
    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.log_error(e, context={"action": "stripe_webhook"})
        # event_type may not be defined if error occurs before parsing
        event_type_str = event_type if 'event_type' in locals() else "unknown"
        raise DatabaseError(
            f"Webhook processing failed: {str(e)}",
            details={"event_type": event_type_str, "original_error": str(e)}
        )


@router.post("/webhooks/paypal")
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Handle PayPal webhook events
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Status response
    """
    try:
        # Parse JSON payload
        payload = await request.json()
        
        # Verify webhook (basic validation)
        verify_paypal_webhook(payload=payload)
        
        event_type = payload.get("event_type")
        resource = payload.get("resource", {})
        
        payment_service = container.get("payment_service")
        
        if event_type == "BILLING.SUBSCRIPTION.UPDATED":
            subscription_id = resource.get("id")
            status = resource.get("status")
            payment_service.update_subscription_status(
                payment_provider_id=subscription_id,
                status=status.lower(),
                db=db
            )
        
        logger.log_info(f"PayPal webhook processed: {event_type}")
        return {"status": "ok"}
    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.log_error(e, context={"action": "paypal_webhook"})
        # event_type may not be defined if error occurs before parsing
        event_type_str = event_type if 'event_type' in locals() else "unknown"
        raise DatabaseError(
            f"Webhook processing failed: {str(e)}",
            details={"event_type": event_type_str, "original_error": str(e)}
        )

