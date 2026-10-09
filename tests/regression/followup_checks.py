"""Offline regressions for the follow-up review; run in a separate process.

HTTP routes, database transactions and socket cleanup use repository code.
The production rate-limit wrapper uses a controlled limiter (SlowAPI is not
installed). AI provider calls and TOTP crypto are controlled test fixtures.
"""

import ast
import asyncio
import importlib.util
import inspect
import json
import os
import runpy
import sys
import tempfile
import threading
import time
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / "tests/regression/security_checks.py"))

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from models.community_models import CommentDB, PostDB
from services.ai_errors import PUBLIC_AI_ERROR
from services.logging_service import logger
from services.websocket_manager import ConnectionManager

SETTINGS = fixture["SETTINGS"]
database = fixture["database"]
extract = fixture["extract"]
ValidationError = fixture["ValidationError"]


class FollowupReviewTests(unittest.TestCase):
    setUp = fixture["ReviewFixTests"].setUp
    factor_service = fixture["ReviewFixTests"].factor_service

    def production_decorator(self, limited=False):
        class Exceeded(Exception):
            pass

        def decorate(*args, **kwargs):
            def apply(endpoint):
                @wraps(endpoint)
                async def wrapped(*args, **kwargs):
                    if limited:
                        raise Exceeded()
                    return await endpoint(*args, **kwargs)
                return wrapped
            return apply

        return extract("backend/middleware/rate_limit.py", "rate_limit", {
            "Callable": Callable, "limiter": types.SimpleNamespace(limit=decorate),
            "Response": Response, "Request": Request, "JSONResponse": JSONResponse,
            "wraps": wraps, "time": time, "RateLimitExceeded": Exceeded,
            "get_remote_address": lambda request: "fixture",
        })

    def test_production_login_preserves_fastapi_parameters(self):
        with patch.object(SETTINGS, "test_mode", False):
            decorator = self.production_decorator()
            rate_module = types.ModuleType("middleware.rate_limit")
            rate_module.rate_limit = lambda limit: decorator(limit, lambda request: "fixture")
            tree = ast.parse((ROOT / "backend/middleware/rate_limit.py").read_text())
            rate_module.RATE_LIMITS = ast.literal_eval(next(
                node.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "RATE_LIMITS" for target in node.targets)
            ))
            spec = importlib.util.spec_from_file_location("review_auth_routes", ROOT / "backend/api/auth_routes.py")
            routes = importlib.util.module_from_spec(spec)
            with patch.dict(sys.modules, {"middleware.rate_limit": rate_module, "review_auth_routes": routes}):
                spec.loader.exec_module(routes)
            auth = Mock()
            auth.authenticate_user.return_value = None
            self.container.register_singleton("auth_service", auth)
            self.container.register_singleton("device_service", Mock())
            self.container.register_singleton("two_factor_auth_service", Mock())
            app = FastAPI()
            app.include_router(routes.router)
            response = TestClient(app).post("/api/auth/login", json={
                "email": "review@example.com", "password": "review-password",
            })
            self.assertEqual(response.status_code, 401, response.text)
            self.assertNotIn("args", inspect.signature(routes.login).parameters)
            auth.authenticate_user.assert_called_once()

    def test_production_rate_limit_keeps_dependencies_and_returns_429(self):
        async def dependency():
            return "review-user"

        for limited, status in ((False, 200), (True, 429)):
            with self.subTest(limited=limited), patch.object(SETTINGS, "test_mode", False):
                app = FastAPI()
                decorator = self.production_decorator(limited)

                @app.get("/tasks")
                @decorator("5/minute", lambda request: "fixture")
                async def tasks(request: Request, limit: int = 5, user=Depends(dependency)):
                    return JSONResponse({"limit": limit, "user": user})

                response = TestClient(app).get("/tasks?limit=7")
                self.assertEqual(response.status_code, status, response.text)
                self.assertEqual(response.headers["X-RateLimit-Limit"], "5")
                if not limited:
                    self.assertEqual(response.json(), {"limit": 7, "user": "review-user"})

    def seed_post(self, post_id="review-parent", status="approved", deleted=False):
        post = PostDB(post_id=post_id, user_id="review_subject", title="sample", content="sample",
                      moderation_status=status, is_deleted=deleted)
        self.db.add(post)
        self.db.commit()
        return post

    def test_pending_post_comments_follow_parent_visibility(self):
        self.seed_post(status="pending")
        self.db.add(CommentDB(comment_id="review-comment", post_id="review-parent", user_id="review_subject",
                              content="private-review-comment", moderation_status="approved"))
        self.db.commit()
        endpoint = "/api/community/posts/review-parent/comments"
        for headers, expected in (({}, 404), ({"x-review-user": "review_viewer"}, 404),
                                  ({"x-review-user": "review_subject"}, 200)):
            response = self.client.get(endpoint, headers=headers)
            self.assertEqual(response.status_code, expected)
            if expected == 404:
                self.assertNotIn("private-review-comment", response.text)
            else:
                self.assertEqual(len(response.json()["comments"]), 1)

    def test_deleted_or_missing_post_comments_are_hidden_even_from_author(self):
        self.seed_post(deleted=True)
        for post_id in ("review-parent", "missing"):
            response = self.client.get(f"/api/community/posts/{post_id}/comments", headers={"x-review-user": "review_subject"})
            self.assertEqual(response.status_code, 404)

    def test_approved_post_with_no_comments_is_public(self):
        self.seed_post()
        response = self.client.get("/api/community/posts/review-parent/comments")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["comments"], [])

    def safe_community(self):
        service = self.container.get("community_service")
        service.nsfw_detector = types.SimpleNamespace(
            check=AsyncMock(return_value={"level": "safe"}), should_block=lambda result: False,
        )
        return service

    def test_comment_creation_rejects_hidden_parent_without_mutation(self):
        self.seed_post(status="pending")
        self.safe_community()
        response = self.client.post("/api/community/posts/review-parent/comments", params={"content": "sample"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.db.query(CommentDB).count(), 0)

    def test_reply_cannot_reference_other_post_or_deleted_comment(self):
        self.seed_post()
        self.seed_post("review-other")
        parent = CommentDB(comment_id="review-comment", post_id="review-other", user_id="review_subject",
                           content="sample", moderation_status="approved")
        self.db.add(parent)
        self.db.commit()
        self.safe_community()
        endpoint = "/api/community/posts/review-parent/comments"
        params = {"content": "sample", "parent_id": parent.comment_id}
        self.assertEqual(self.client.post(endpoint, params=params).status_code, 404)
        parent.post_id = "review-parent"
        parent.is_deleted = True
        self.db.commit()
        self.assertEqual(self.client.post(endpoint, params=params).status_code, 404)
        parent.is_deleted = False
        self.db.commit()
        self.assertEqual(self.client.post(endpoint, params=params).status_code, 200)

    def admin_family(self):
        family_id = self.family.create_family("review_subject", "Review family", self.db)["family_id"]
        self.family.invite_member(family_id, "review_subject", "review_admin", "admin", self.db)
        self.family.accept_invitation(family_id, "review_admin", self.db)
        return family_id

    def test_family_invites_cannot_grant_owner_or_admin_by_admin(self):
        family_id = self.admin_family()
        for inviter, role in (("review_subject", "owner"), ("review_admin", "owner"), ("review_admin", "admin")):
            with self.subTest(inviter=inviter, role=role), self.assertRaises(ValidationError):
                self.family.invite_member(family_id, inviter, "review_other", role, self.db)
        response = self.client.post(f"/api/families/{family_id}/invite", headers={"x-review-user": "review_subject"},
                                    json={"invitee_user_id": "review_other", "role": "owner"})
        self.assertEqual(response.status_code, 422)
        for role in ("viewer", "member"):
            self.family.invite_member(family_id, "review_admin", "review_" + role, role, self.db)

    def test_family_admin_cannot_remove_creator_or_peer(self):
        family_id = self.admin_family()
        self.family.invite_member(family_id, "review_subject", "review_peer", "admin", self.db)
        self.family.accept_invitation(family_id, "review_peer", self.db)
        for target in ("review_subject", "review_peer"):
            with self.assertRaises(ValidationError):
                self.family.remove_member(family_id, target, "review_admin", self.db)

    def test_creator_can_revoke_legacy_owner_without_granting_it_authority(self):
        family_id = self.admin_family()
        self.db.add(database.FamilyMemberDB(family_id=family_id, user_id="review_legacy", role="owner", status="active"))
        self.db.commit()
        with self.assertRaises(ValidationError):
            self.family.invite_member(family_id, "review_legacy", "review_other", "member", self.db)
        self.assertTrue(self.family.remove_member(family_id, "review_legacy", "review_subject", self.db))
        self.assertEqual(self.db.query(database.FamilyMemberDB).filter_by(user_id="review_legacy").one().status, "inactive")

    def test_legacy_owner_invitation_cannot_be_accepted(self):
        family_id = self.admin_family()
        self.db.add(database.FamilyMemberDB(family_id=family_id, user_id="review_legacy", role="owner", status="pending"))
        self.db.commit()
        with self.assertRaises(ValidationError):
            self.family.accept_invitation(family_id, "review_legacy", self.db)

    def test_backup_code_is_single_use_across_concurrent_sqlite_sessions(self):
        service = self.factor_service()
        with tempfile.TemporaryDirectory(prefix="factor-race-", dir=ROOT / "do-not-upload/data") as folder:
            engine = create_engine(f"sqlite:///{Path(folder) / 'race.db'}", connect_args={"check_same_thread": False})
            try:
                database.Base.metadata.create_all(engine)
                sessions = sessionmaker(bind=engine)
                with sessions() as db:
                    db.add(database.TwoFactorAuthDB(user_id="review_subject", is_enabled=True,
                                                    secret_key=os.urandom(20).hex(), backup_codes=["REVIEWCODE"]))
                    db.commit()
                barrier = threading.Barrier(2)

                def verify(_):
                    with sessions() as db:
                        def loaded(session, instance):
                            if isinstance(instance, database.TwoFactorAuthDB):
                                barrier.wait(timeout=5)
                        event.listen(db, "loaded_as_persistent", loaded)
                        return service.verify_2fa("review_subject", "REVIEWCODE", db)

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(verify, range(2)))
                self.assertEqual(sorted(results), [False, True])
                with sessions() as db:
                    self.assertEqual(db.query(database.TwoFactorAuthDB).one().backup_codes, [])
            finally:
                engine.dispose()

    def test_disconnect_cleans_all_subscriptions_and_is_idempotent(self):
        manager = ConnectionManager()
        socket, other = object(), object()
        manager.active_connections["review_subject"] = {socket, other}
        manager.connection_users.update({socket: "review_subject", other: "review_subject"})
        manager.task_subscriptions.update({"one": {socket}, "two": {socket}, "shared": {socket, other}})
        manager.disconnect(socket)
        manager.disconnect(socket)
        self.assertNotIn(socket, manager.connection_users)
        self.assertEqual(manager.task_subscriptions, {"shared": {other}})
        self.assertEqual(manager.active_connections, {"review_subject": {other}})

    def ai_service(self):
        detector = types.SimpleNamespace(check=AsyncMock(return_value={"safe": True}), should_block=lambda result: False)
        ai_class = extract("core/services/ai_service.py", "AIService", {
            "Dict": Dict, "List": List, "Any": Any, "Optional": Optional, "AsyncGenerator": AsyncGenerator,
            "datetime": datetime, "json": json, "get_nsfw_detector": lambda: detector,
            "logger": logger, "PUBLIC_AI_ERROR": PUBLIC_AI_ERROR,
        })
        ai = object.__new__(ai_class)
        ai.provider_name = "review"
        ai.provider = types.SimpleNamespace(chat=AsyncMock(side_effect=RuntimeError("provider-private-review-marker")))
        ai._base_system_prompt = "review"
        return ai

    def test_ai_fallback_responses_hide_provider_diagnostics(self):
        ai = self.ai_service()
        calls = (
            ("chat", ("sample", {}), {"system_prompt": "review"}),
            ("crisis_response", ("sample", {}, []), {"system_prompt": "review"}),
            ("analyze_tracking", ([], {}), {"system_prompt": "review"}),
            ("generate_tracking_summary", ([], {}), {}),
            ("analyze_emotional_state", ({}, []), {}),
        )
        for method, args, kwargs in calls:
            with self.subTest(method=method), patch.object(logger, "log_error") as logged:
                result = asyncio.run(getattr(ai, method)(*args, **kwargs))
                self.assertEqual(result["error"], PUBLIC_AI_ERROR)
                self.assertNotIn("provider-private-review-marker", json.dumps(result))
                logged.assert_called_once()

    def test_ai_stream_masks_error_chunks_and_raised_exceptions(self):
        ai = self.ai_service()

        async def stream(**kwargs):
            yield {"type": "chunk", "content": "sample"}
            yield {"type": "error", "content": "provider-private-review-marker", "debug": "private-review-marker"}
            raise RuntimeError("provider-private-review-marker")

        ai.provider.chat_stream = stream

        async def consume():
            return [chunk async for chunk in ai.chat_stream("sample", {}, system_prompt="review")]

        with patch.object(logger, "log_error"):
            result = asyncio.run(consume())
        self.assertEqual(result, [{"type": "chunk", "content": "sample"},
                                  {"type": "error", "content": PUBLIC_AI_ERROR},
                                  {"type": "error", "content": PUBLIC_AI_ERROR}])

    def test_provider_stream_adapters_hide_exceptions(self):
        from services.ai_providers import OpenAIProvider, ClaudeProvider, GeminiProvider
        for provider_class in (OpenAIProvider, ClaudeProvider, GeminiProvider):
            with self.subTest(provider=provider_class.__name__):
                provider = object.__new__(provider_class)
                failing = Mock(side_effect=RuntimeError("provider-private-review-marker"))
                provider.model = types.SimpleNamespace(generate_content=failing)
                provider.client = types.SimpleNamespace(
                    chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("provider-private-review-marker")))),
                    messages=types.SimpleNamespace(stream=failing),
                )

                async def consume():
                    return [chunk async for chunk in provider.chat_stream([])]

                with patch.object(logger, "log_error"):
                    self.assertEqual(asyncio.run(consume()), [{"type": "error", "content": PUBLIC_AI_ERROR}])

    def test_worker_persists_public_error_and_logs_original_exception(self):
        db = Mock()
        queue = Mock()
        queue.claim_task.return_value = True
        queue.get_task.return_value = {"started_at": datetime.now().isoformat()}
        worker_class = extract("workers/ai_worker.py", "AIWorker", {
            "Dict": Dict, "Any": Any, "datetime": datetime, "SessionLocal": lambda: db,
            "TaskStatus": fixture["TaskStatus"], "PUBLIC_AI_ERROR": PUBLIC_AI_ERROR, "logger": logger,
        })
        worker = object.__new__(worker_class)
        worker.worker_id = "review-worker"
        worker.task_queue = queue
        original = RuntimeError("worker-private-review-marker")
        worker._process_chat_task = AsyncMock(side_effect=original)
        with patch.object(logger, "log_error") as logged, self.assertRaises(RuntimeError):
            asyncio.run(worker.process_task({"task_id": "review-task", "task_type": "ai_chat", "task_data": {}, "user_id": "review_subject"}))
        self.assertEqual(queue.update_task_status.call_args.kwargs["error"], PUBLIC_AI_ERROR)
        self.assertIs(logged.call_args.args[0], original)
        db.close.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
