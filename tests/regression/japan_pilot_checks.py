"""HTTP, SQLite and Japan time regressions; authentication and AI network are fixtures."""

import asyncio
import json
import runpy
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
review = runpy.run_path(str(ROOT / "tests/regression/review_235a4c9_checks.py"))
fixture, database, settings = review["fixture"], review["database"], review["SETTINGS"]

from fastapi import Header, HTTPException
from api import auth_routes, night_mode_routes, personalization_routes, pilot_routes, tracking_routes
from models.schemas import TrackingEntry, User
from services import nsfw_detector
from services.cache_service import get_cache
from services.logging_service import logger
from services.relaxation_service import RelaxationService
from services.suggestion_validator import SuggestionValidator
from services.tracking_service import TrackingService


async def pilot_user(x_review_user: Optional[str] = Header(None)):
    if not x_review_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return User(id=1, user_id=x_review_user, email="pilot@example.com",
                is_active=x_review_user != "review_disabled", created_at=datetime.utcnow())


class JapanPilotTests(unittest.TestCase):
    def setUp(self):
        fixture["ReviewFixTests"].setUp(self)
        self.client.app.include_router(auth_routes.router)
        self.client.app.include_router(pilot_routes.router)
        self.client.app.include_router(tracking_routes.router)
        self.client.app.include_router(personalization_routes.router)
        self.client.app.include_router(night_mode_routes.router)
        self.client.app.dependency_overrides[fixture["fixture_current_user"]] = pilot_user
        self.container.register_singleton("tracking_service", TrackingService())
        self.container.register_singleton("relaxation_service", RelaxationService())
        for name, value in [("institution_user_ids", "review_staff"), ("ai_provider", "fixture")]:
            change = patch.object(settings, name, value, create=True)
            change.start()
            self.addCleanup(change.stop)
        get_cache().clear()
        self.addCleanup(get_cache().clear)
        self.staff = {"x-review-user": "review_staff"}
        self.family = {"x-review-user": "review_family"}

    def profile(self):
        return {"name": "Pilot support service", "municipality": "Pilot area", "contact": "Contact the local office",
                "hours": "Check with the office", "retention_notice": "Ask the operator about retention and deletion.",
                "resources": [{"name": "Official source", "url": "https://www.cfa.go.jp/policies/boshihoken",
                               "description": "Maternal and child health", "hours": "Check source", "checked_on": "2026-01-01"}]}

    def test_public_directory_is_available_without_auth_or_ai(self):
        response = self.client.get("/api/pilot")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profile"]["resources"], [])
        self.assertEqual(set(response.json()), {"profile", "updated_at", "ai_provider"})

    def test_entrance_selection_and_regular_accounts_cannot_edit(self):
        self.assertEqual(self.client.post("/api/pilot/organization", json=self.profile()).status_code, 401)
        for headers in [self.family, {"x-review-user": "review_disabled"}]:
            self.assertEqual(self.client.get("/api/pilot/organization", headers=headers).status_code, 403)
            self.assertEqual(self.client.post("/api/pilot/organization", headers=headers, json=self.profile()).status_code, 403)
        self.assertEqual(self.db.query(database.PilotProfileDB).count(), 0)

    def test_admin_and_institution_permissions_are_separate(self):
        with patch.object(settings, "admin_user_ids", "review_family", create=True):
            self.assertEqual(self.client.get("/api/pilot/organization", headers=self.family).status_code, 403)

    def test_staff_save_persists_and_public_view_contains_no_editor_identity(self):
        response = self.client.post("/api/pilot/organization", headers=self.staff, json=self.profile())
        self.assertEqual(response.status_code, 200, response.text)
        self.db.expire_all()
        record = self.db.query(database.PilotProfileDB).one()
        self.assertEqual(record.updated_by, "review_staff")
        self.assertEqual(record.profile, self.profile())
        public = self.client.get("/api/pilot")
        self.assertEqual(public.json()["profile"], self.profile())
        self.assertNotIn("review_staff", public.text)
        self.assertIsNotNone(public.json()["updated_at"])

    def test_revoked_staff_cannot_read_management_or_save(self):
        with patch.object(settings, "institution_user_ids", ""):
            self.assertEqual(self.client.get("/api/pilot/organization", headers=self.staff).status_code, 403)
            self.assertEqual(self.client.post("/api/pilot/organization", headers=self.staff, json=self.profile()).status_code, 403)

    def test_staff_can_clear_optional_resource_text_and_checked_date(self):
        profile = self.profile()
        self.assertEqual(self.client.post("/api/pilot/organization", headers=self.staff, json=profile).status_code, 200)
        profile["resources"][0].update(description="", hours="", checked_on=None)
        response = self.client.post("/api/pilot/organization", headers=self.staff, json=profile)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get("/api/pilot").json()["profile"], profile)

    def test_source_urls_and_dates_are_validated_without_changing_saved_data(self):
        self.client.post("/api/pilot/organization", headers=self.staff, json=self.profile())
        for url in ["javascript:alert(1)", "http://example.com", "https://user:password@example.com"]:
            data = self.profile()
            data["resources"][0]["url"] = url
            self.assertEqual(self.client.post("/api/pilot/organization", headers=self.staff, json=data).status_code, 422)
        data = self.profile()
        data["resources"][0]["checked_on"] = "2999-01-01"
        self.assertEqual(self.client.post("/api/pilot/organization", headers=self.staff, json=data).status_code, 422)
        data = self.profile()
        data["resources"] *= 11
        self.assertEqual(self.client.post("/api/pilot/organization", headers=self.staff, json=data).status_code, 422)
        self.assertEqual(self.client.get("/api/pilot").json()["profile"], self.profile())

    def test_directory_rejects_hidden_family_payload_fields(self):
        data = {**self.profile(), "user_id": "review_family", "health_records": ["private marker"]}
        self.assertEqual(self.client.post("/api/pilot/organization", headers=self.staff, json=data).status_code, 422)

    def test_institution_role_never_grants_access_to_another_users_records(self):
        self.assertEqual(self.client.get("/api/tracking/review_family", headers=self.staff).status_code, 403)
        self.assertEqual(self.client.post("/api/tracking", headers=self.staff,
            json={"user_id": "review_family", "entry_type": "feeding"}).status_code, 403)

    def test_public_directory_never_serializes_private_tracking(self):
        self.db.add(database.TrackingEntryDB(user_id="review_family", entry_type="mood", notes="private-family-marker"))
        self.db.commit()
        public = self.client.get("/api/pilot")
        self.assertNotIn("private-family-marker", public.text)
        self.assertNotIn("review_family", public.text)

    def test_daily_summary_uses_japan_midnight_and_excludes_next_day(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                current = cls(2026, 10, 10, 15, 30, tzinfo=timezone.utc)
                return current.astimezone(tz) if tz else current.replace(tzinfo=None)
        for timestamp in [datetime(2026, 10, 10, 14, 59), datetime(2026, 10, 10, 15, 1),
                          datetime(2026, 10, 11, 14, 59), datetime(2026, 10, 11, 15)]:
            self.db.add(database.TrackingEntryDB(user_id="review_family", entry_type="feeding", timestamp=timestamp))
        self.db.commit()
        with patch("services.tracking_service.datetime", FixedDateTime):
            result = asyncio.run(TrackingService().generate_daily_summary("review_family", self.db))
        self.assertEqual(result["date"], "2026-10-11")
        self.assertEqual(result["entries_count"], 2)

    def test_recovery_is_saveable_and_aware_timestamps_are_normalized_to_utc(self):
        response = self.client.post("/api/tracking", headers=self.family, json={"entry_type": "recovery", "weight_kg": 55,
            "timestamp": "2026-10-11T00:30:00+09:00"})
        self.assertEqual(response.status_code, 200, response.text)
        entry = self.db.query(database.TrackingEntryDB).one()
        self.assertEqual(entry.timestamp, datetime(2026, 10, 10, 15, 30))

    def test_private_record_notes_save_without_external_moderation(self):
        moderation = AsyncMock(return_value=types.SimpleNamespace(results=[types.SimpleNamespace(
            flagged=False, categories=types.SimpleNamespace(model_dump=lambda: {}),
            category_scores=types.SimpleNamespace(model_dump=lambda: {}))]))
        detector = object.__new__(nsfw_detector.NSFWDetector)
        detector.provider = "openai"
        detector.enabled = True
        detector.strict_mode = False
        detector._unsafe_keywords = []
        detector._openai_client = types.SimpleNamespace(moderations=types.SimpleNamespace(create=moderation))
        records = [
            {"entry_type": "feeding", "notes": "private-care-note"},
            {"entry_type": "mood", "mood_notes": "private-mood-note"},
            {"entry_type": "recovery", "recovery_notes": "private-recovery-note", "notes": "private-parent-note"},
        ]
        with patch.object(nsfw_detector, "_nsfw_detector", detector):
            for record in records:
                response = self.client.post("/api/tracking", headers=self.family, json=record)
                self.assertEqual(response.status_code, 200, response.text)
            saved = self.client.get("/api/tracking/review_family", headers=self.family)
        moderation.assert_not_awaited()
        self.assertEqual(saved.status_code, 200)
        by_type = {entry["entry_type"]: entry for entry in saved.json()}
        for record in records:
            for key, value in record.items():
                self.assertEqual(by_type[record["entry_type"]][key], value)

    def test_registration_validation_logs_never_include_password_input(self):
        marker = "PrivatePasswordFixture123!"
        with patch.object(logger.logger, "error") as logged:
            response = self.client.post("/api/auth/register", json={"password": marker})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(marker, response.text)
        self.assertTrue(logged.called)
        self.assertNotIn(marker, str(logged.call_args_list))
        self.assertIn("Request validation failed", str(logged.call_args_list))

    def test_tracking_validation_logs_never_include_health_notes(self):
        marker = "private-health-note-fixture"
        with patch.object(logger.logger, "error") as logged:
            response = self.client.post("/api/tracking", headers=self.family, json={"notes": marker})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(marker, response.text)
        self.assertTrue(logged.called)
        self.assertNotIn(marker, str(logged.call_args_list))
        self.assertIn("entry_type", str(logged.call_args_list))

    def ai(self, fail=False):
        ai = review["followup"]["FollowupReviewTests"].ai_service(self)
        ai.validator = SuggestionValidator()
        if not fail:
            ai.provider.chat = AsyncMock(return_value={"text": "今の気持ちを一緒に整理しましょう。"})
        self.container.register_singleton("ai_service", ai)
        return ai

    def test_japanese_checkin_uses_japanese_prompt_and_japan_contacts(self):
        ai = self.ai()
        response = self.client.post("/api/emotional-checkin", headers=self.family, json={"language": "ja",
            "overwhelmed_level": 8, "anxiety_level": 4, "support_level": 2})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["analysis_available"])
        prompt = ai.provider.chat.call_args.kwargs["messages"][0]["content"]
        self.assertTrue(any(ord(character) > 127 for character in prompt))
        self.assertIn("119", response.text)
        for number in ["988", "741741", "1-800"]:
            self.assertNotIn(number, response.text)

    def test_provider_failure_stays_unknown_in_japanese(self):
        self.ai(fail=True)
        response = self.client.post("/api/emotional-checkin", headers=self.family, json={"language": "ja",
            "overwhelmed_level": 2, "anxiety_level": 2, "support_level": 8})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertFalse(result["analysis_available"])
        self.assertEqual(result["risk_level"], "unknown")
        self.assertIn("現在", result["assessment"])
        self.assertIsNone(result["escalation_needed"])

    def test_optional_welcome_age_ranges_are_not_treated_as_exact_days(self):
        context = self.ai()._format_user_context({"babyAge": "1-2", "birthType": "vaginal", "feedingType": "mixed"})
        self.assertIn("1–2 weeks", context)
        self.assertIn("mixed", context)
        self.assertNotIn("days old", context)

    def save_context(self, context, user_id="review_family"):
        response = self.client.post("/api/user/context", headers=self.family,
                                    json={"user_id": user_id, "context": context})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["context"]

    def test_partial_context_updates_preserve_omitted_fields_and_allow_explicit_clearing(self):
        original = {"babyName": "saved nickname", "babyAge": "2-3m", "language": "en",
                    "notifications": True, "preferences": {"tone": "warm"}}
        self.save_context(original)
        updated = self.save_context({"babyName": "", "notifications": False})
        self.assertEqual(updated, {**original, "babyName": "", "notifications": False})
        self.assertEqual(self.client.get("/api/user/review_family/context", headers=self.family).json(), updated)
        self.db.expire_all()
        self.assertEqual(self.db.query(database.UserContextDB).one().context, updated)
        from utils.user_preferences import get_user_language_preference
        self.assertEqual(asyncio.run(get_user_language_preference("review_family", self.db)), "en")

    def test_welcome_skip_preserves_existing_server_profile(self):
        original = {"babyName": "saved nickname", "babyAge": "2-3m", "birthType": "c-section",
                    "feedingType": "mixed", "language": "ja", "notifications": True}
        self.save_context(original)
        self.assertEqual(self.save_context({"language": "ja"}), original)
        self.assertEqual(self.client.get("/api/user/review_family/context", headers=self.family).json(), original)

    def test_partial_context_update_does_not_authorize_another_account(self):
        original = {"babyName": "private nickname", "language": "ja"}
        self.save_context(original)
        response = self.client.post("/api/user/context", headers=self.staff,
                                    json={"user_id": "review_family", "context": {"babyName": ""}})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/api/user/review_family/context", headers=self.family).json(), original)

    def assert_night_language(self, language, suffix):
        service = self.container.get("relaxation_service")
        for method, path, field, expected in [
            ("post", "relaxation", "guide", service.relaxation_guides[language]),
            ("post", "breathing", "exercise", service.breathing_exercises[language]),
            ("get", "safety-tips", "tips", service.get_safety_tips(language)["tips"]),
            ("get", "quick-calm", "tips", service.quick_calm_tips[language]),
        ]:
            with self.subTest(path=path, language=language, suffix=suffix):
                response = getattr(self.client, method)(f"/api/night-mode/{path}{suffix}", headers=self.family)
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()[field]
                if path == "quick-calm":
                    self.assertTrue(all(tip in expected for tip in result))
                elif path == "safety-tips":
                    self.assertEqual(result, expected)
                else:
                    self.assertIn(result, expected)

    def test_night_mode_honors_explicit_language_and_regional_tags(self):
        self.save_context({"language": "en"})
        self.assert_night_language("ja", "?language=ja")
        self.assert_night_language("ja", "?language=ja-JP")
        self.save_context({"language": "ja"})
        self.assert_night_language("en", "?language=en")
        self.assert_night_language("en", "?language=en-US")

    def test_night_mode_without_query_keeps_saved_language_fallback(self):
        for language in ["ja", "en", "ja-JP", "en-US"]:
            self.save_context({"language": language})
            self.assert_night_language(language.split("-")[0], "")

    def test_night_mode_rejects_unsupported_language(self):
        for method, path in [("post", "relaxation"), ("post", "breathing"), ("get", "safety-tips"), ("get", "quick-calm")]:
            response = getattr(self.client, method)(f"/api/night-mode/{path}?language=unsupported", headers=self.family)
            self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
