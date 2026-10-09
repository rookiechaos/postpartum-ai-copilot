"""Verify payment notifications before any subscription state is changed."""

import hashlib
import hmac
import time
from typing import Mapping, Optional

import httpx
from fastapi import HTTPException

from config.settings import get_settings
from exceptions import ServiceUnavailableError


def verify_stripe_webhook(
    payload: bytes,
    signature: Optional[str],
    webhook_secret: Optional[str] = None,
) -> bool:
    secret = webhook_secret or get_settings().stripe_webhook_secret
    if not secret:
        raise ServiceUnavailableError("Stripe webhook verification is not configured")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    try:
        fields = [part.strip().split("=", 1) for part in signature.split(",")]
        timestamp = next(value for key, value in fields if key == "t")
        signatures = [value for key, value in fields if key == "v1"]
        if abs(time.time() - int(timestamp)) > 300 or not signatures:
            raise ValueError("Expired or missing signature")
        signed_payload = timestamp.encode() + b"." + payload
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, value) for value in signatures):
            raise ValueError("Signature mismatch")
    except (ValueError, StopIteration):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from None
    return True


async def verify_paypal_webhook(
    payload: dict,
    headers: Optional[Mapping[str, str]] = None,
    webhook_id: Optional[str] = None,
) -> bool:
    """Use PayPal's authenticated verification API; configuration errors fail closed."""
    settings = get_settings()
    expected_id = webhook_id or settings.paypal_webhook_id
    if not expected_id or not settings.paypal_client_id or not settings.paypal_client_secret:
        raise ServiceUnavailableError("PayPal webhook verification is not configured")
    if not isinstance(payload, dict) or not isinstance(payload.get("resource"), dict) or not payload.get("event_type"):
        raise HTTPException(status_code=400, detail="Invalid PayPal event")
    received = {key.lower(): value for key, value in (headers or {}).items()}
    field_headers = {
        "auth_algo": "paypal-auth-algo",
        "cert_url": "paypal-cert-url",
        "transmission_id": "paypal-transmission-id",
        "transmission_sig": "paypal-transmission-sig",
        "transmission_time": "paypal-transmission-time",
    }
    if any(not received.get(name) for name in field_headers.values()):
        raise HTTPException(status_code=400, detail="Missing PayPal signature headers")
    verification = {field: received[name] for field, name in field_headers.items()}
    verification.update(webhook_id=expected_id, webhook_event=payload)
    base_url = "https://api-m.paypal.com" if settings.paypal_environment == "live" else "https://api-m.sandbox.paypal.com"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            token_response = await client.post(
                f"{base_url}/v1/oauth2/token",
                auth=httpx.BasicAuth(settings.paypal_client_id, settings.paypal_client_secret),
                data={"grant_type": "client_credentials"},
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            response = await client.post(
                f"{base_url}/v1/notifications/verify-webhook-signature",
                headers={"Authorization": f"Bearer {access_token}"},
                json=verification,
            )
            response.raise_for_status()
            verified = response.json().get("verification_status") == "SUCCESS"
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise ServiceUnavailableError("PayPal webhook verification is temporarily unavailable") from None
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid PayPal signature")
    return True
