"""
Webhook Verification Utilities - Verify webhook signatures from payment providers
Webhook verification utilities - verify payment provider webhook signatures
"""

from typing import Optional
from fastapi import HTTPException, Request
import hmac
import hashlib
import json
from config.settings import get_settings
from services.logging_service import logger


def verify_stripe_webhook(
    payload: bytes,
    signature: Optional[str],
    webhook_secret: Optional[str] = None
) -> bool:
    """
    Verify Stripe webhook signature
    
    Args:
        payload: Raw request body as bytes
        signature: Stripe signature from header
        webhook_secret: Stripe webhook secret (optional, uses settings if not provided)
        
    Returns:
        True if signature is valid, False otherwise
        
    Raises:
        HTTPException: If signature is missing or invalid
    """
    settings = get_settings()
    secret = webhook_secret or settings.stripe_webhook_secret
    
    if not secret:
        # In production, webhook secret is required
        if not settings.debug and not settings.test_mode:
            logger.log_error(
                ValueError("Stripe webhook secret not configured in production"),
                context={"action": "verify_stripe_webhook"}
            )
            raise HTTPException(
                status_code=500,
                detail="Stripe webhook secret not configured. Webhook verification is required in production."
            )
        # In development/test mode, allow webhooks without verification
        logger.log_info("Stripe webhook secret not configured, skipping verification (development mode)")
        return True
    
    if not signature:
        logger.log_error(
            ValueError("Missing Stripe signature header"),
            context={"action": "verify_stripe_webhook"}
        )
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    try:
        # Stripe signature format: timestamp,signature1,signature2
        elements = signature.split(",")
        timestamp = None
        signatures = []
        
        for element in elements:
            if "=" in element:
                key, value = element.split("=", 1)
                if key == "t":
                    timestamp = value
                elif key == "v1":
                    signatures.append(value)
        
        if not timestamp or not signatures:
            raise ValueError("Invalid signature format")
        
        # Create signed payload
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        
        # Compute expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Verify signature
        is_valid = any(
            hmac.compare_digest(expected_signature, sig)
            for sig in signatures
        )
        
        if not is_valid:
            logger.log_error(
                ValueError("Invalid Stripe webhook signature"),
                context={"action": "verify_stripe_webhook"}
            )
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")
        
        return True
    except Exception as e:
        logger.log_error(e, context={"action": "verify_stripe_webhook"})
        raise HTTPException(status_code=400, detail=f"Webhook verification failed: {str(e)}")


def verify_paypal_webhook(
    payload: dict,
    webhook_id: Optional[str] = None
) -> bool:
    """
    Verify PayPal webhook (basic validation)
    
    Note: Full PayPal webhook verification requires making an API call to PayPal.
    This is a basic validation that checks required fields.
    
    Args:
        payload: Webhook payload as dictionary
        webhook_id: PayPal webhook ID (optional, uses settings if not provided)
        
    Returns:
        True if payload is valid, False otherwise
        
    Raises:
        HTTPException: If payload is invalid
    """
    settings = get_settings()
    expected_webhook_id = webhook_id or settings.paypal_webhook_id
    
    if not expected_webhook_id:
        # In production, webhook ID is required
        if not settings.debug and not settings.test_mode:
            logger.log_error(
                ValueError("PayPal webhook ID not configured in production"),
                context={"action": "verify_paypal_webhook"}
            )
            raise HTTPException(
                status_code=500,
                detail="PayPal webhook ID not configured. Webhook verification is required in production."
            )
        # In development/test mode, allow webhooks without verification
        logger.log_info("PayPal webhook ID not configured, skipping verification (development mode)")
        return True
    
    # Basic validation: check required fields
    required_fields = ["event_type", "resource"]
    for field in required_fields:
        if field not in payload:
            logger.log_error(
                ValueError(f"Missing required field: {field}"),
                context={"action": "verify_paypal_webhook"}
            )
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Note: Full verification would require:
    # 1. Getting webhook verification URL from PayPal
    # 2. Making POST request to verify webhook
    # 3. This is typically done asynchronously after processing
    
    logger.log_info("PayPal webhook basic validation passed (full verification requires API call)")
    return True
