"""Offline regressions for the third review; run in a separate process.

HTTP routes, persistence, session revalidation and AI parsing use repository
code. Authentication dependencies, JWT/password crypto and provider/network
calls are controlled fixtures. This does not test third-party crypto itself.
"""

import asyncio
import json
import runpy
import secrets
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[2]
followup = runpy.run_path(str(ROOT / "tests/regression/followup_checks.py"))
fixture = followup["fixture"]
SETTINGS = fixture["SETTINGS"]
database = fixture["database"]

# Decorator coverage lives in followup_checks; no SlowAPI installation needed.
rate_module = types.ModuleType("middleware.rate_limit")
rate_module.rate_limit = lambda *args, **kwargs: lambda endpoint: endpoint
rate_module.RATE_LIMITS = {key: "100/minute" for key in ("default", "chat", "tracking", "task", "auth")}
sys.modules["middleware.rate_limit"] = rate_module

from fastapi import FastAPI, Header, HTTPException, WebSocketDisconnect
from fastapi.testclient import TestClient
from api import monitoring_routes, notification_routes, personalization_routes, tracking_routes, websocket_routes
from dependencies.database import get_db
from middleware.admin import require_admin
from models.schemas import UserCreate
from services.cache_service import get_cache
from services.health_check_service import HealthCheckService
from services.logging_service import logger
from services.notification_service import NotificationService
from services.tracking_service import TrackingService
from services.websocket_manager import ConnectionManager


class Socket:
    def __init__(self, receive=None):
        self.query_params = {"token": "signed-fixture"}
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.send_json = AsyncMock()
        self.receive_text = AsyncMock(side_effect=receive)


class ThirdReviewTests(unittest.TestCase):
    def setUp(self):
        fixture["ReviewFixTests"].setUp(self)
        self.db.add(database.UserDB(user_id="review_viewer", email="review@example.com",
                                   hashed_password="fixture", is_active=True))
        self.db.commit()
        get_cache().clear()
        self.addCleanup(get_cache().clear)
        settings = patch.object(SETTINGS, "admin_user_ids", None, create=True)
        settings.start()
        self.addCleanup(settings.stop)
        log = patch.object(logger, "log_error")
        self.logged_errors = log.start()
        self.addCleanup(log.stop)

    def auth_service(self):
        service, decoder = fixture["ReviewFixTests"].auth_service(self)
        service.create_user.__globals__["secrets"] = secrets
        service.get_password_hash = lambda password: "controlled-password-hash"
        service.verify_password = lambda password, stored: stored == "controlled-password-hash"
        return service, decoder

    def test_public_registration_cannot_claim_an_admin_identity_or_email_role(self):
        SETTINGS.admin_user_ids = "reserved_admin"
        service, _ = self.auth_service()
        with patch.object(SETTINGS, "admin_emails", "review-admin@example.com", create=True):
            created = service.create_user(UserCreate(email="review-admin@example.com",
                password="ReviewPassword123!", user_id="reserved_admin"), self.db)
            self.assertNotEqual(created.user_id, "reserved_admin")
            self.assertTrue(created.is_active)
            signed_in = service.authenticate_user(created.email, "ReviewPassword123!", self.db)
            with self.assertRaises(HTTPException) as denied:
                asyncio.run(require_admin(signed_in))
            self.assertEqual(denied.exception.status_code, 403)
            SETTINGS.admin_user_ids = created.user_id  # Explicit operator grant.
            self.assertEqual(asyncio.run(require_admin(signed_in)).user_id, created.user_id)
            SETTINGS.admin_user_ids = None
            with self.assertRaises(HTTPException):
                asyncio.run(require_admin(signed_in))

    def test_existing_unverified_email_account_never_inherits_admin(self):
        current = asyncio.run(fixture["fixture_current_user"]("review_viewer"))
        SETTINGS.admin_user_ids = "another_user"
        with patch.object(SETTINGS, "admin_emails", current.email, create=True):
            with self.assertRaises(HTTPException):
                asyncio.run(require_admin(current))
        SETTINGS.admin_user_ids = current.user_id
        current.is_active = False
        with self.assertRaises(HTTPException):
            asyncio.run(require_admin(current))

    def socket_auth(self):
        service, decoder = self.auth_service()
        decoder.decode.return_value = {"sub": "review_viewer", "type": "access"}
        self.container.register_singleton("auth_service", service)
        self.container.register_singleton("task_queue", self.queue)
        return service, decoder

    def enable_factor(self):
        factor = database.TwoFactorAuthDB(user_id="review_viewer", secret_key="fixture-factor", is_enabled=True)
        self.db.add(factor)
        self.db.commit()
        return factor

    def reject_incoming(self, revoke):
        task_id = self.queue.create_task("ai_chat", {}, "review_viewer", self.db)
        manager = ConnectionManager()

        async def receive():
            revoke()
            return json.dumps({"type": "subscribe_task", "task_id": task_id})

        socket = Socket(receive)
        with patch.object(websocket_routes, "connection_manager", manager):
            asyncio.run(websocket_routes.websocket_endpoint(socket))
        socket.accept.assert_awaited_once()
        socket.close.assert_awaited_once_with(code=1008, reason="Authentication required")
        self.assertEqual([call.args[0]["type"] for call in socket.send_json.await_args_list], ["connection"])
        self.assertFalse(manager.task_subscriptions)
        self.assertFalse(manager.session_validators)

    def test_socket_cannot_subscribe_after_enabling_second_factor(self):
        self.socket_auth()
        self.reject_incoming(self.enable_factor)

    def test_asgi_socket_closes_on_factor_change_before_subscription(self):
        self.socket_auth()
        manager = ConnectionManager()
        app = FastAPI()
        app.include_router(websocket_routes.router)
        with patch.object(websocket_routes, "connection_manager", manager):
            with TestClient(app).websocket_connect("/ws?token=signed-fixture") as socket:
                self.assertEqual(socket.receive_json()["type"], "connection")
                self.enable_factor()
                socket.send_json({"type": "subscribe_task", "task_id": "private-task"})
                with self.assertRaises(WebSocketDisconnect) as closed:
                    socket.receive_json()
                self.assertEqual(closed.exception.code, 1008)
        self.assertFalse(manager.active_connections)
        self.assertFalse(manager.task_subscriptions)

    def test_asgi_idle_socket_revalidation_cancels_receive_and_closes_cleanly(self):
        _, decoder = self.socket_auth()
        manager = ConnectionManager()
        app = FastAPI()
        app.include_router(websocket_routes.router)
        with patch.object(websocket_routes, "connection_manager", manager), \
             patch.object(websocket_routes, "AUTH_RECHECK_INTERVAL_SECONDS", 0.01):
            with TestClient(app).websocket_connect("/ws?token=signed-fixture") as socket:
                self.assertEqual(socket.receive_json()["type"], "connection")
                decoder.decode.side_effect = ValueError("expired-fixture")
                with self.assertRaises(WebSocketDisconnect) as closed:
                    socket.receive_json()
                self.assertEqual(closed.exception.code, 1008)
        self.assertFalse(manager.active_connections)

    def test_socket_cannot_subscribe_after_account_deactivation(self):
        self.socket_auth()

        def deactivate():
            self.db.query(database.UserDB).filter_by(user_id="review_viewer").update({"is_active": False})
            self.db.commit()

        self.reject_incoming(deactivate)

    def test_expired_socket_cannot_receive_any_private_push(self):
        service, decoder = self.socket_auth()

        def valid():
            with database.SessionLocal() as db:
                return service.verify_token("signed-fixture", db=db) is not None

        async def exercise():
            for channel in ("personal", "user", "task"):
                decoder.decode.side_effect = None
                manager, socket = ConnectionManager(), Socket()
                await manager.connect(socket, "review_viewer", valid)
                manager.subscribe_to_task(socket, "private-task")
                decoder.decode.side_effect = ValueError("expired-fixture")
                if channel == "personal":
                    await manager.send_personal_message({"private": True}, socket)
                elif channel == "user":
                    await manager.send_to_user("review_viewer", {"private": True})
                else:
                    await manager.broadcast_task_update("private-task", {"private": True})
                self.assertEqual(socket.send_json.await_count, 1)
                socket.close.assert_awaited_once()
                self.assertEqual(manager.get_total_connections(), 0)
                self.assertFalse(manager.task_subscriptions)

        asyncio.run(exercise())

    def reject_factor_push(self, change):
        service, decoder = self.socket_auth()
        factor = self.enable_factor()
        decoder.decode.return_value["mfa_version"] = service.get_two_factor_version("review_viewer", self.db)

        def valid():
            with database.SessionLocal() as db:
                return service.verify_token("signed-fixture", db=db) is not None

        async def exercise():
            manager, socket = ConnectionManager(), Socket()
            await manager.connect(socket, "review_viewer", valid)
            manager.subscribe_to_task(socket, "private-task")
            change(factor)
            self.db.commit()
            await manager.broadcast_task_update("private-task", {"private": True})
            self.assertEqual(socket.send_json.await_count, 1)
            socket.close.assert_awaited_once()

        asyncio.run(exercise())

    def test_rotated_factor_revokes_existing_socket_pushes(self):
        self.reject_factor_push(lambda factor: setattr(factor, "secret_key", "rotated-fixture"))

    def test_disabled_factor_revokes_existing_socket_pushes(self):
        self.reject_factor_push(lambda factor: setattr(factor, "is_enabled", False))

    def test_idle_socket_is_closed_when_token_expires(self):
        _, decoder = self.socket_auth()
        manager = ConnectionManager()

        async def receive():
            decoder.decode.side_effect = ValueError("expired-fixture")
            await asyncio.Event().wait()

        socket = Socket(receive)
        with patch.object(websocket_routes, "connection_manager", manager), \
             patch.object(websocket_routes, "AUTH_RECHECK_INTERVAL_SECONDS", 0.01):
            asyncio.run(asyncio.wait_for(websocket_routes.websocket_endpoint(socket), timeout=1))
        socket.close.assert_awaited_once()
        self.assertFalse(manager.active_connections)

    def test_valid_socket_keeps_task_ownership_checks(self):
        self.socket_auth()
        owned = self.queue.create_task("ai_chat", {}, "review_viewer", self.db)
        other = self.queue.create_task("ai_chat", {}, "other_user", self.db)
        manager = ConnectionManager()
        frames = iter([json.dumps({"type": "subscribe_task", "task_id": owned}),
                       json.dumps({"type": "subscribe_task", "task_id": other}), "[]"])

        async def receive():
            try:
                return next(frames)
            except StopIteration:
                raise WebSocketDisconnect()

        socket = Socket(receive)
        with patch.object(websocket_routes, "connection_manager", manager):
            asyncio.run(websocket_routes.websocket_endpoint(socket))
        messages = [call.args[0] for call in socket.send_json.await_args_list]
        self.assertEqual(messages[1]["task_id"], owned)
        self.assertEqual(messages[2]["message"], "Unauthorized task subscription")
        self.assertEqual(messages[3]["message"], "Invalid message format")
        self.assertFalse(manager.task_subscriptions)

    def test_task_push_revalidates_the_routes_current_user(self):
        self.socket_auth()
        task_id = self.queue.create_task("ai_chat", {}, "review_viewer", self.db)
        manager = ConnectionManager()
        reads = 0

        async def receive():
            nonlocal reads
            reads += 1
            if reads == 1:
                return json.dumps({"type": "subscribe_task", "task_id": task_id})
            self.db.query(database.UserDB).filter_by(user_id="review_viewer").update({"is_active": False})
            self.db.commit()
            await manager.broadcast_task_update(task_id, {"result": "private-fixture"})
            raise WebSocketDisconnect()

        socket = Socket(receive)
        with patch.object(websocket_routes, "connection_manager", manager):
            asyncio.run(websocket_routes.websocket_endpoint(socket))
        self.assertEqual([call.args[0]["type"] for call in socket.send_json.await_args_list], ["connection", "subscription"])
        socket.close.assert_awaited_once()
        self.assertFalse(manager.task_subscriptions)

    def monitoring_client(self, db):
        async def authenticated(x_review_user: Optional[str] = Header(None)):
            if not x_review_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            return await fixture["fixture_current_user"](x_review_user)

        app = FastAPI()
        app.include_router(monitoring_routes.router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[fixture["fixture_current_user"]] = authenticated
        return TestClient(app)

    def test_public_health_is_finite_and_returns_failure_status(self):
        broken = Mock()
        broken.execute.side_effect = RuntimeError("private-database-fixture-marker")
        health = HealthCheckService()
        client = self.monitoring_client(broken)
        with patch.object(monitoring_routes, "get_health_check_service", return_value=health):
            failed = client.get("/api/monitoring/health")
            self.assertEqual(failed.status_code, 503)
            self.assertEqual(set(failed.json()), {"status", "timestamp"})
            self.assertEqual(failed.json()["status"], "degraded")
            self.assertNotIn("private-database-fixture-marker", failed.text)
            broken.execute.side_effect = None
            self.assertEqual(client.get("/api/monitoring/health").status_code, 200)
        self.logged_errors.assert_called()

    def test_diagnostics_require_explicit_admin_and_sanitize_errors(self):
        broken = Mock()
        broken.execute.side_effect = RuntimeError("private-database-fixture-marker")
        health = HealthCheckService()
        health.check_ai_provider = lambda: {"status": "configured"}
        health.check_task_queue = lambda db: {"status": "healthy"}
        health.check_system_resources = lambda: {"status": "healthy"}
        client = self.monitoring_client(broken)
        SETTINGS.admin_user_ids = "review_admin"
        with patch.object(monitoring_routes, "get_health_check_service", return_value=health):
            for path in ("health/details", "metrics", "tasks", "system"):
                self.assertEqual(client.get("/api/monitoring/" + path).status_code, 401)
                self.assertEqual(client.get("/api/monitoring/" + path, headers={"X-Review-User": "review_viewer"}).status_code, 403)
            response = client.get("/api/monitoring/health/details", headers={"X-Review-User": "review_admin"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["checks"]["database"]["error"], "Database health check failed")
            self.assertNotIn("private-database-fixture-marker", response.text)

    def test_outer_health_failure_does_not_leak_configuration(self):
        client = self.monitoring_client(self.db)
        with patch.object(monitoring_routes, "get_health_check_service", side_effect=RuntimeError("private-config-fixture")):
            response = client.get("/api/monitoring/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-config-fixture", response.text)

    def test_component_diagnostics_never_return_original_exceptions(self):
        health = HealthCheckService()
        marker = "private-component-fixture"
        broken = Mock()
        broken.query.side_effect = RuntimeError(marker)
        settings = types.SimpleNamespace(ai_provider="fixture", get_ai_api_key=Mock(side_effect=RuntimeError(marker)))
        resources = types.SimpleNamespace(cpu_percent=Mock(side_effect=RuntimeError(marker)))
        with patch("services.health_check_service.get_settings", return_value=settings):
            ai = health.check_ai_provider()
        queue = health.check_task_queue(broken)
        with patch.dict(sys.modules, {"psutil": resources}):
            system = health.check_system_resources()
        for result in (ai, queue, system):
            self.assertEqual(result["status"], "error")
            self.assertNotIn(marker, json.dumps(result))
            self.assertTrue(result["error"])

    def test_context_frontend_payload_persists_and_round_trips(self):
        self.container.register_singleton("tracking_service", TrackingService())
        self.client.app.include_router(personalization_routes.router)
        context = {"babyName": "Sample", "babyAge": "1-2m", "birthType": "vaginal",
                   "feedingType": "mixed", "notifications": False, "darkMode": True, "language": "en"}
        response = self.client.post("/api/user/context", json={"user_id": "review_viewer", "context": context})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["context"], context)
        self.db.expire_all()
        self.assertEqual(self.db.query(database.UserContextDB).one().context, context)
        get_cache().clear()  # The GET must read persistent data.
        self.assertEqual(self.client.get("/api/user/review_viewer/context").json(), context)
        context["babyName"] = "Updated sample"
        updated = self.client.post("/api/user/context", json={"context": context})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(self.client.get("/api/user/review_viewer/context").json(), context)

    def test_context_update_rejects_another_users_identity(self):
        self.container.register_singleton("tracking_service", TrackingService())
        self.client.app.include_router(personalization_routes.router)
        response = self.client.post("/api/user/context", json={"user_id": "other_user", "context": {"babyName": "sample"}})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db.query(database.UserContextDB).count(), 0)

    def emotional_client(self, fail=False):
        ai = followup["FollowupReviewTests"].ai_service(self)
        if not fail:
            ai.provider.chat = AsyncMock(return_value={"text": "Consider reaching out for support."})
        self.container.register_singleton("ai_service", ai)
        self.container.register_singleton("tracking_service", TrackingService())
        self.client.app.include_router(tracking_routes.router)
        return ai

    def test_emotional_checkin_reaches_provider_and_parses_real_model(self):
        ai = self.emotional_client()
        for level, risk in ((10, "high"), (2, "low")):
            response = self.client.post("/api/emotional-checkin", json={
                "overwhelmed_level": level, "anxiety_level": level, "support_level": 1})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["risk_level"], risk)
            self.assertTrue(response.json()["analysis_available"])
        self.assertEqual(ai.provider.chat.await_count, 2)

    def test_emotional_provider_failure_is_unknown_and_preserves_failure_flag(self):
        ai = self.emotional_client(fail=True)
        response = self.client.post("/api/emotional-checkin", json={
            "overwhelmed_level": 10, "anxiety_level": 10, "support_level": 1})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["risk_level"], "unknown")
        self.assertFalse(body["analysis_available"])
        self.assertIsNone(body["escalation_needed"])
        self.assertTrue(body["error"])
        self.assertNotIn("provider-private-review-marker", response.text)
        ai.provider.chat.assert_awaited_once()

    def test_notification_metadata_survives_http_database_and_recurrence(self):
        service = NotificationService()
        self.container.register_singleton("notification_service", service)
        self.client.app.include_router(notification_routes.router, prefix="/api/notifications")
        metadata = {"sample": True, "nested": {"value": 3}}
        response = self.client.post("/api/notifications/", json={"notification_type": "custom", "title": "sample",
            "message": "sample", "scheduled_time": "2026-10-10T00:00:00", "is_recurring": True,
            "recurrence_pattern": "daily", "metadata": metadata})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["metadata"], metadata)
        self.db.expire_all()
        self.assertEqual(self.db.query(database.NotificationDB).one().notification_metadata, metadata)
        self.assertFalse(service.mark_notification_sent(response.json()["id"], self.db))
        receipt = self.client.post(f"/api/notifications/{response.json()['id']}/acknowledge", json={})
        self.assertEqual(receipt.status_code, 200, receipt.text)
        self.assertTrue(receipt.json()["acknowledged"])
        rows = self.db.query(database.NotificationDB).all()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row.notification_metadata == metadata for row in rows))
        result = self.client.get("/api/notifications/?include_sent=true")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertTrue(all(row["metadata"] == metadata for row in result.json()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
