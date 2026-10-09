"""Isolated regressions for the repository review fixes.

Run this file in its own process. Routes, SQLAlchemy queries and state changes
are real; settings and authentication are controlled fixtures. Extracted auth
methods test factor enforcement without testing third-party JWT/TOTP crypto.
"""

import ast
import asyncio
import hashlib
import hmac
import json
import os
import runpy
import sys
import time
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "core")]
SETTINGS = types.SimpleNamespace(
    database_url="sqlite://", debug=False, test_mode=True,
    paypal_webhook_id=None, paypal_client_id=None, paypal_client_secret=None,
    paypal_environment="sandbox", stripe_webhook_secret=None,
    jwt_secret_key="", algorithm="HS256", access_token_expire_minutes=30,
    refresh_token_expire_days=30,
)
config = types.ModuleType("config.settings")
config.get_settings = lambda: SETTINGS
sys.modules["config.settings"] = config

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from models import database
from models.schemas import Token, TokenData, User, UserLogin, RefreshTokenRequest
from services.logging_service import logger

database.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
database.SessionLocal = sessionmaker(bind=database.engine)


async def fixture_current_user(x_review_user: str = Header("review_viewer")):
    return User(id=1, user_id=x_review_user, email="review@example.com", is_active=True, created_at=datetime.utcnow())


async def fixture_optional_user():
    return None


auth_dependency = types.ModuleType("middleware.auth")
auth_dependency.get_current_user = fixture_current_user
auth_dependency.get_optional_user = fixture_optional_user
sys.modules["middleware.auth"] = auth_dependency

from dependencies.container import get_container
from exceptions import DatabaseError, PostpartumException, ServiceUnavailableError, ValidationError
from middleware.error_handler import postpartum_exception_handler, validation_exception_handler, http_exception_handler
from middleware.security import SecurityHeadersMiddleware
from models.community_models import PostDB
from services.community_service import CommunityService
from services.family_service import FamilyService
from services.payment_service import PaymentService
from services.task_queue import TaskQueue, TaskStatus
from utils import webhook_verification
from utils.runtime_paths import RUNTIME_ROOT, resolve_runtime_path
from api import community_routes, family_routes, payment_routes


def extract(path, name, scope):
    tree = ast.parse((ROOT / path).read_text())
    node = next(item for item in tree.body if getattr(item, "name", None) == name)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node.decorator_list = []
        node.args.defaults = []
        for argument in node.args.args:
            argument.annotation = None
        node.returns = None
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(ROOT / path), "exec"), scope)
    return scope[name]


class ReviewFixTests(unittest.TestCase):
    def setUp(self):
        database.Base.metadata.drop_all(database.engine)
        database.Base.metadata.create_all(database.engine)
        SETTINGS.debug = False
        SETTINGS.paypal_webhook_id = "review-webhook"
        SETTINGS.paypal_client_id = "review-client"
        SETTINGS.paypal_client_secret = "review-placeholder"
        SETTINGS.stripe_webhook_secret = None
        self.payments = PaymentService()
        self.family = FamilyService()
        self.queue = TaskQueue()
        self.container = get_container()
        self.container.clear()
        self.container.register_singleton("payment_service", self.payments)
        self.container.register_singleton("family_service", self.family)
        self.container.register_singleton("community_service", object.__new__(CommunityService))
        app = FastAPI()
        app.add_exception_handler(PostpartumException, postpartum_exception_handler)
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        app.add_exception_handler(StarletteHTTPException, http_exception_handler)
        app.add_middleware(SecurityHeadersMiddleware)
        app.include_router(payment_routes.router, prefix="/api/payments")
        app.include_router(family_routes.router, prefix="/api/families")
        app.include_router(community_routes.router)
        self.client = TestClient(app, raise_server_exceptions=False)
        self.db = database.SessionLocal()
        self.addCleanup(self.db.close)

    def seed_subscription(self, user="review_subject", provider="paypal", plan="premium", state="active"):
        subscription = database.SubscriptionDB(
            user_id=user, plan=plan, status=state,
            payment_provider=provider, payment_provider_id="review-subscription",
        )
        self.db.add(subscription)
        self.db.commit()
        return subscription

    def seed_family(self):
        family_id = self.family.create_family("review_subject", "Review family", self.db)["family_id"]
        self.family.invite_member(family_id, "review_subject", "review_viewer", "viewer", self.db)
        self.family.accept_invitation(family_id, "review_viewer", self.db)
        self.db.add(database.TrackingEntryDB(user_id="review_subject", entry_type="mood", notes="private-review-note"))
        self.db.commit()
        return family_id

    def claim(self):
        task_id = self.queue.create_task("ai_chat", {"query": "sample"}, "review_subject", self.db)
        self.assertTrue(self.queue.claim_task(task_id, "worker", self.db))
        started = datetime.fromisoformat(self.queue.get_task(task_id, self.db)["started_at"])
        return task_id, started

    def test_paid_plans_cannot_be_self_activated(self):
        for plan in ("premium", "enterprise"):
            response = self.client.post("/api/payments/subscriptions", json={"plan": plan, "payment_provider": "stripe"})
            self.assertEqual(response.status_code, 503)
        self.assertEqual(self.db.query(database.SubscriptionDB).count(), 0)

    def test_free_plan_does_not_bind_client_provider_identifier(self):
        response = self.client.post("/api/payments/subscriptions", json={
            "plan": "free", "payment_provider": "stripe", "payment_provider_id": "untrusted-id",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.db.query(database.SubscriptionDB).one().payment_provider_id)

    def test_legacy_unverified_paid_plan_does_not_grant_access(self):
        self.seed_subscription(plan="enterprise")
        self.assertFalse(self.payments.check_subscription_access("review_subject", "priority_support", self.db))

    def test_unsigned_paypal_event_cannot_change_state(self):
        subscription = self.seed_subscription()
        response = self.client.post("/api/payments/webhooks/paypal", json={
            "event_type": "BILLING.SUBSCRIPTION.UPDATED",
            "resource": {"id": "review-subscription", "status": "CANCELLED"},
        })
        self.assertEqual(response.status_code, 400)
        self.db.refresh(subscription)
        self.assertEqual(subscription.status, "active")

    @staticmethod
    def paypal_headers():
        return {name: "review-value" for name in (
            "paypal-auth-algo", "paypal-cert-url", "paypal-transmission-id",
            "paypal-transmission-sig", "paypal-transmission-time",
        )}

    def paypal_transport(self, verification_status):
        import httpx
        seen = []
        def handler(request):
            seen.append(request)
            if request.url.path == "/v1/oauth2/token":
                return httpx.Response(200, json={"access_token": "review-provider-token"})
            verification = json.loads(request.content)
            self.assertEqual(verification["webhook_id"], SETTINGS.paypal_webhook_id)
            self.assertEqual(verification["webhook_event"]["resource"]["id"], "review-subscription")
            self.assertEqual(request.headers["authorization"], "Bearer review-provider-token")
            return httpx.Response(200, json={"verification_status": verification_status})
        original_client = httpx.AsyncClient
        return lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs), seen

    def test_verified_paypal_event_updates_only_matching_provider(self):
        paypal = self.seed_subscription()
        stripe = self.seed_subscription(user="review_other", provider="stripe")
        factory, seen = self.paypal_transport("SUCCESS")
        with patch.object(webhook_verification.httpx, "AsyncClient", side_effect=factory):
            response = self.client.post("/api/payments/webhooks/paypal", headers=self.paypal_headers(), json={
                "event_type": "BILLING.SUBSCRIPTION.UPDATED",
                "resource": {"id": "review-subscription", "status": "CANCELLED"},
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(seen), 2)
        self.db.refresh(paypal)
        self.db.refresh(stripe)
        self.assertEqual(paypal.status, "cancelled")
        self.assertEqual(stripe.status, "active")

    def test_paypal_failed_verification_preserves_subscription(self):
        subscription = self.seed_subscription()
        factory, _ = self.paypal_transport("FAILURE")
        with patch.object(webhook_verification.httpx, "AsyncClient", side_effect=factory):
            response = self.client.post("/api/payments/webhooks/paypal", headers=self.paypal_headers(), json={
                "event_type": "BILLING.SUBSCRIPTION.UPDATED",
                "resource": {"id": "review-subscription", "status": "CANCELLED"},
            })
        self.assertEqual(response.status_code, 400)
        self.db.refresh(subscription)
        self.assertEqual(subscription.status, "active")

    def test_missing_paypal_configuration_fails_closed(self):
        SETTINGS.paypal_client_secret = None
        with self.assertRaises(ServiceUnavailableError):
            asyncio.run(webhook_verification.verify_paypal_webhook({}, headers={}))

    def test_stripe_signature_and_timestamp_are_verified(self):
        secret = os.urandom(32).hex()
        body = b'{"type":"review-event"}'
        timestamp = str(int(time.time()))
        digest = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        signature = f"t={timestamp},v1={digest}"
        self.assertTrue(webhook_verification.verify_stripe_webhook(body, signature, secret))
        with self.assertRaises(HTTPException):
            webhook_verification.verify_stripe_webhook(body + b" ", signature, secret)
        with self.assertRaises(HTTPException):
            webhook_verification.verify_stripe_webhook(body, f"t=1,v1={digest}", secret)
        with self.assertRaises(ServiceUnavailableError):
            webhook_verification.verify_stripe_webhook(body, None)

    def test_anonymous_posts_cannot_be_mapped_by_author_filter(self):
        self.db.add(PostDB(post_id="review-anonymous", user_id="review_viewer", title="sample", content="sample", is_anonymous=True, moderation_status="approved"))
        self.db.commit()
        self.assertEqual(self.client.get("/api/community/posts?user_id=review_viewer").json()["posts"], [])
        self.assertEqual(len(self.client.get("/api/community/posts").json()["posts"]), 1)
        self.assertEqual(len(self.client.get("/api/community/posts/mine").json()["posts"]), 1)

    def test_unapproved_post_is_visible_only_to_author(self):
        self.db.add(PostDB(post_id="review-pending", user_id="review_viewer", title="sample", content="sample", moderation_status="pending"))
        self.db.commit()
        self.assertEqual(self.client.get("/api/community/posts/review-pending").status_code, 404)
        service = self.container.get("community_service")
        self.assertEqual(asyncio.run(service.get_post("review-pending", "review_viewer", self.db))["post_id"], "review-pending")

    def test_family_sharing_requires_explicit_opt_in_and_can_be_revoked(self):
        family_id = self.seed_family()
        endpoint = f"/api/families/{family_id}/shared-data"
        self.assertEqual(self.client.get(endpoint).json()["data"], [])
        for enabled in (True, False, True, False):
            self.family.share_tracking_data(family_id, "review_subject", enabled, self.db)
            entries = self.client.get(endpoint).json()["data"]
            self.assertEqual(len(entries), int(enabled))

    def test_family_summary_does_not_read_nonsharing_member(self):
        family_id = self.seed_family()
        tracking = types.SimpleNamespace(generate_daily_summary=AsyncMock(return_value={"summary": "sample"}))
        result = asyncio.run(self.family.generate_family_summary(family_id, "review_viewer", tracking_service=tracking, ai_service=object(), db=self.db))
        self.assertEqual(result["summary"], {})
        tracking.generate_daily_summary.assert_not_called()
        self.family.share_tracking_data(family_id, "review_subject", True, self.db)
        asyncio.run(self.family.generate_family_summary(family_id, "review_viewer", tracking_service=tracking, ai_service=object(), db=self.db))
        self.assertEqual(tracking.generate_daily_summary.call_args.kwargs["user_id"], "review_subject")

    def test_sharing_endpoint_cannot_set_another_members_preference(self):
        family_id = self.seed_family()
        response = self.client.post(f"/api/families/{family_id}/sharing", json={"share_tracking": True, "user_id": "review_subject"})
        self.assertEqual(response.status_code, 200)
        subject = self.db.query(database.FamilyMemberDB).filter_by(family_id=family_id, user_id="review_subject").one()
        self.db.refresh(subject)
        self.assertFalse(subject.permissions["share_tracking"])
        denied = self.client.post(f"/api/families/{family_id}/sharing", headers={"x-review-user": "outsider"}, json={"share_tracking": True})
        self.assertEqual(denied.status_code, 400)

    def test_family_tasks_are_not_claimed_by_ai_workers(self):
        family_id = self.seed_family()
        task_id = self.family.create_family_task(family_id, "review_viewer", "Review task", db=self.db)["task_id"]
        self.assertEqual(self.queue.get_pending_tasks(self.db), [])
        self.assertFalse(self.queue.claim_task(task_id, "worker", self.db))
        self.assertEqual(self.queue.get_task(task_id, self.db)["status"], "pending")

    def test_cancelled_task_cannot_be_completed_or_retried(self):
        for terminal_status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task_id, started = self.claim()
            self.assertTrue(self.queue.cancel_task(task_id, "review_subject", self.db))
            self.assertFalse(self.queue.update_task_status(task_id, terminal_status, self.db, worker_id="worker", started_at=started))
            self.assertEqual(self.queue.get_task(task_id, self.db)["status"], "cancelled")

    def test_old_execution_cannot_write_after_retry_even_on_same_worker(self):
        task_id, first_started = self.claim()
        self.assertTrue(self.queue.update_task_status(task_id, TaskStatus.FAILED, self.db, worker_id="worker", started_at=first_started))
        self.assertTrue(self.queue.claim_task(task_id, "worker", self.db))
        second_started = datetime.fromisoformat(self.queue.get_task(task_id, self.db)["started_at"])
        self.assertNotEqual(first_started, second_started)
        self.assertFalse(self.queue.update_task_status(task_id, TaskStatus.COMPLETED, self.db, worker_id="worker", started_at=first_started))
        self.assertTrue(self.queue.update_task_status(task_id, TaskStatus.COMPLETED, self.db, worker_id="worker", started_at=second_started))

    def test_worker_result_requires_execution_ownership(self):
        task_id, started = self.claim()
        self.assertFalse(self.queue.update_task_status(task_id, TaskStatus.COMPLETED, self.db))
        self.assertFalse(self.queue.update_task_status(task_id, TaskStatus.COMPLETED, self.db, worker_id="other", started_at=started))
        self.assertTrue(self.queue.update_task_status(task_id, TaskStatus.COMPLETED, self.db, result={"text": "sample"}, worker_id="worker", started_at=started))
        self.assertEqual(self.queue.get_task(task_id, self.db)["result"], {"text": "sample"})

    def test_timeout_cannot_be_overwritten_by_late_result(self):
        task_id, started = self.claim()
        task = self.db.query(database.TaskDB).filter_by(task_id=task_id).one()
        task.timeout_seconds = 1
        task.started_at = datetime.utcnow() - timedelta(seconds=5)
        self.db.commit()
        self.assertEqual(self.queue.check_timeout_tasks(self.db), [task_id])
        self.assertFalse(self.queue.update_task_status(task_id, TaskStatus.COMPLETED, self.db, worker_id="worker", started_at=started))
        self.assertEqual(self.queue.get_task(task_id, self.db)["status"], "failed")

    def auth_service(self):
        decoder = Mock()
        scope = {
            "Optional": Optional, "Dict": Dict, "Any": Any, "Session": Session,
            "datetime": datetime, "timedelta": timedelta, "hashlib": hashlib,
            "UserDB": database.UserDB, "TwoFactorAuthDB": database.TwoFactorAuthDB,
            "User": User, "UserCreate": object, "TokenData": TokenData,
            "ValidationError": ValidationError, "JWTError": ValueError,
            "jwt": decoder, "get_settings": lambda: SETTINGS,
        }
        service = extract("core/services/auth_service.py", "AuthService", scope)()
        return service, decoder

    def seed_factor(self):
        factor = database.TwoFactorAuthDB(user_id="review_subject", is_enabled=True, secret_key=os.urandom(20).hex())
        self.db.add(factor)
        self.db.commit()
        return factor

    def test_existing_access_and_refresh_tokens_require_current_factor_proof(self):
        factor = self.seed_factor()
        service, decoder = self.auth_service()
        for token_type in ("access", "refresh"):
            decoder.decode.return_value = {"sub": "review_subject", "type": token_type}
            self.assertIsNone(service.verify_token("signed-fixture", token_type, db=self.db))
            decoder.decode.return_value["mfa_version"] = service.get_two_factor_version("review_subject", self.db)
            self.assertIsNotNone(service.verify_token("signed-fixture", token_type, db=self.db))
        factor.secret_key = os.urandom(20).hex()
        self.db.commit()
        self.assertIsNone(service.verify_token("signed-fixture", "refresh", db=self.db))

    def test_login_issues_no_tokens_until_second_factor_passes(self):
        service = Mock()
        service.authenticate_user.return_value = types.SimpleNamespace(user_id="review_subject", email="review@example.com")
        service.get_two_factor_version.return_value = "verified-factor-version"
        service.access_token_expire = 30
        service.create_access_token.return_value = "signed-access-fixture"
        service.create_refresh_token.return_value = "signed-refresh-fixture"
        factor = Mock()
        factor.get_2fa_status.return_value = {"is_enabled": True}
        factor.verify_2fa.return_value = False
        self.container.register_singleton("auth_service", service)
        self.container.register_singleton("device_service", Mock())
        self.container.register_singleton("two_factor_auth_service", factor)
        login = extract("backend/api/auth_routes.py", "login", {
            "container": self.container, "Token": Token, "timedelta": timedelta,
            "HTTPException": HTTPException, "status": status,
        })
        request = types.SimpleNamespace(headers={}, client=None)
        credentials = UserLogin(email="review@example.com", password="review-password")
        response = asyncio.run(login(request, credentials, self.db))
        self.assertTrue(response.requires_2fa)
        self.assertIsNone(response.access_token)
        self.assertIsNone(response.refresh_token)
        service.create_access_token.assert_not_called()
        factor.verify_2fa.assert_not_called()
        credentials.verification_token = "123456"
        with self.assertRaises(HTTPException):
            asyncio.run(login(request, credentials, self.db))
        service.create_access_token.assert_not_called()
        factor.verify_2fa.return_value = True
        response = asyncio.run(login(request, credentials, self.db))
        self.assertFalse(response.requires_2fa)
        self.assertEqual(service.create_refresh_token.call_args.kwargs["data"]["mfa_version"], "verified-factor-version")
        service.create_access_token.reset_mock()
        service.get_two_factor_version.side_effect = ["old-factor-version", "new-factor-version"]
        with self.assertRaises(HTTPException):
            asyncio.run(login(request, credentials, self.db))
        service.create_access_token.assert_not_called()

    def test_refresh_checks_current_factor_and_preserves_verified_claims(self):
        service = Mock()
        service.access_token_expire = 30
        service.verify_token.return_value = TokenData(user_id="review_subject", email="review@example.com", mfa_version="verified-factor-version")
        service.get_user_by_id.return_value = types.SimpleNamespace(user_id="review_subject", email="review@example.com", is_active=True)
        service.create_access_token.return_value = "signed-access-fixture"
        service.create_refresh_token.return_value = "signed-refresh-fixture"
        self.container.register_singleton("auth_service", service)
        refresh = extract("backend/api/auth_routes.py", "refresh_token", {
            "container": self.container, "Token": Token, "timedelta": timedelta,
            "HTTPException": HTTPException, "status": status,
        })
        response = asyncio.run(refresh(object(), RefreshTokenRequest(refresh_token="signed-refresh-fixture"), None, self.db))
        service.verify_token.assert_called_once_with("signed-refresh-fixture", token_type="refresh", db=self.db)
        self.assertEqual(service.create_access_token.call_args.kwargs["data"]["mfa_version"], "verified-factor-version")
        self.assertIsNotNone(response.access_token)

    def test_http_authentication_rejects_password_only_token_after_enabling_two_factor(self):
        self.seed_factor()
        self.db.add(database.UserDB(user_id="review_subject", email="review@example.com", hashed_password="review-hash", is_active=True))
        self.db.commit()
        service, decoder = self.auth_service()
        decoder.decode.return_value = {"sub": "review_subject", "type": "access"}
        authenticate = extract("backend/middleware/auth.py", "get_current_user", {
            "auth_service": service, "HTTPException": HTTPException, "status": status,
        })
        credentials = types.SimpleNamespace(credentials="signed-access-fixture")
        with self.assertRaises(HTTPException) as denied:
            asyncio.run(authenticate(credentials, self.db))
        self.assertEqual(denied.exception.status_code, 401)
        decoder.decode.return_value["mfa_version"] = service.get_two_factor_version("review_subject", self.db)
        self.assertEqual(asyncio.run(authenticate(credentials, self.db)).user_id, "review_subject")

    def test_websocket_authentication_rejects_password_only_token(self):
        self.seed_factor()
        service, decoder = self.auth_service()
        decoder.decode.return_value = {"sub": "review_subject", "type": "access"}
        self.container.register_singleton("auth_service", service)
        manager = Mock()
        manager.connect = AsyncMock()
        websocket = types.SimpleNamespace(query_params={"token": "signed-access-fixture"}, close=AsyncMock())
        endpoint = extract("backend/api/websocket_routes.py", "websocket_endpoint", {
            "container": self.container, "SessionLocal": database.SessionLocal,
            "logger": logger, "connection_manager": manager,
        })
        asyncio.run(endpoint(websocket))
        websocket.close.assert_awaited_once()
        manager.connect.assert_not_called()

    def factor_service(self):
        otp = types.SimpleNamespace(TOTP=lambda secret: types.SimpleNamespace(verify=lambda *args, **kwargs: False))
        scope = {"Dict": Dict, "Any": Any, "Session": Session, "datetime": datetime,
                 "TwoFactorAuthDB": database.TwoFactorAuthDB, "logger": logger,
                 "ValidationError": ValidationError, "DatabaseError": DatabaseError, "pyotp": otp}
        return extract("core/services/two_factor_auth_service.py", "TwoFactorAuthService", scope)()

    def test_backup_code_is_persistently_consumed(self):
        factor = self.seed_factor()
        factor.backup_codes = ["REVIEWCODE"]
        self.db.commit()
        service = self.factor_service()
        self.assertTrue(service.verify_2fa("review_subject", "REVIEWCODE", self.db))
        self.db.expire_all()
        self.assertFalse(service.verify_2fa("review_subject", "REVIEWCODE", self.db))

    def test_factor_status_database_error_does_not_disable_two_factor(self):
        broken_db = Mock()
        broken_db.query.side_effect = RuntimeError("review-database-failure")
        with self.assertRaises(DatabaseError):
            self.factor_service().get_2fa_status("review_subject", broken_db)

    def test_runtime_paths_support_legacy_defaults_and_reject_escape(self):
        self.assertEqual(resolve_runtime_path("../do-not-upload/logs", "logs"), RUNTIME_ROOT / "logs")
        self.assertTrue((RUNTIME_ROOT / "logs").is_dir())
        with self.assertRaises(ValueError):
            resolve_runtime_path("../outside-review", "logs")

    def test_legacy_sqlite_path_is_shared_by_api_and_worker(self):
        previous_directory = Path.cwd()
        try:
            for directory in (ROOT / "backend", ROOT / "workers"):
                os.chdir(directory)
                with patch.object(SETTINGS, "database_url", "sqlite:///../do-not-upload/data/review-path.db"):
                    loaded = runpy.run_path(str(ROOT / "backend/models/database.py"))
                self.assertEqual(Path(loaded["engine"].url.database), RUNTIME_ROOT / "data/review-path.db")
                loaded["engine"].dispose()
        finally:
            os.chdir(previous_directory)

    def test_production_custom_errors_hide_internal_details(self):
        request = Request({"type": "http", "method": "GET", "path": "/review", "headers": []})
        response = asyncio.run(postpartum_exception_handler(request, DatabaseError("private-review-marker", details={"original_error": "private-review-marker"})))
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"private-review-marker", response.body)

    def test_wrapped_database_errors_do_not_leak_through_http_exception(self):
        self.container.register_singleton("community_service", types.SimpleNamespace(
            get_posts=AsyncMock(side_effect=DatabaseError("private-review-marker")),
        ))
        response = self.client.get("/api/community/posts")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private-review-marker", response.text)
        SETTINGS.debug = True
        self.assertIn("private-review-marker", self.client.get("/api/community/posts").text)

    def test_validation_errors_do_not_expose_inputs_or_exception_context(self):
        request = Request({"type": "http", "method": "POST", "path": "/review", "headers": []})
        error = RequestValidationError([{"type": "value_error", "loc": ("body", "password"), "msg": "Invalid input", "input": "private-review-marker", "ctx": {"error": ValueError("private-review-marker")}}])
        response = asyncio.run(validation_exception_handler(request, error))
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(b"private-review-marker", response.body)

    def test_api_responses_are_not_cacheable(self):
        response = self.client.get("/api/community/posts")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_worker_inherits_required_configuration_and_runtime_paths(self):
        import yaml
        configuration = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        api = configuration["services"]["api"]
        worker = configuration["services"]["worker"]
        self.assertEqual(api["environment"]["JWT_SECRET_KEY"], worker["environment"]["JWT_SECRET_KEY"])
        self.assertIn(":?", worker["environment"]["JWT_SECRET_KEY"])
        self.assertEqual(worker["command"], "python /app/workers/worker.py")
        self.assertIn("runtime_data:/app/do-not-upload", worker["volumes"])
        dockerfile = (ROOT / "backend/Dockerfile").read_text()
        self.assertIn("COPY workers/ /app/workers/", dockerfile)
        self.assertIn("COPY locales/ /app/locales/", dockerfile)

    def test_openai_pin_satisfies_published_langchain_constraint(self):
        from packaging.specifiers import SpecifierSet
        requirements = (ROOT / "backend/requirements.txt").read_text().splitlines()
        pinned = next(line.split("==")[1] for line in requirements if line.startswith("openai=="))
        # langchain-openai 0.0.2 release metadata, linked in the fix notes.
        self.assertIn(pinned, SpecifierSet(">=1.6.1,<2.0.0"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
