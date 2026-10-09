"""Regression tests for staged, untracked, historical, and binary privacy leaks."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("privacy_scan", ROOT / "scripts/privacy_scan.py")
scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scanner)


class PrivacyContentTests(unittest.TestCase):
    def categories(self, data, name="sample.txt"):
        return {f["category"] for f in scanner.scan_bytes("test", name, data)}

    def test_detects_private_ipv4_and_ipv6(self):
        values = [".".join(["10", "23", "45", "67"]), ":".join(["fd12", "3456", "", "1"])]
        for value in values:
            with self.subTest(value=value):
                self.assertIn("ip-address", self.categories(value.encode()))

    def test_allows_documentation_and_loopback_addresses(self):
        self.assertEqual(self.categories(b"127.0.0.1 0.0.0.0 ::1 192.0.2.10 198.51.100.10 203.0.113.10 2001:db8::1"), set())

    def test_does_not_treat_dependency_versions_as_ips(self):
        self.assertNotIn("ip-address", self.categories(b"package==1.2.300.400"))

    def test_detects_paths_inside_binary_files(self):
        data = b"\0" + ("/Users/" + "fixture-user/code.py").encode() + b"\0"
        self.assertIn("personal-path", self.categories(data, "cache.pyc"))
        self.assertIn("compiled-python", self.categories(data, "cache.pyc"))

    def test_detects_secret_and_withholds_value(self):
        secret = "sk-" + "a" * 35
        findings = scanner.scan_bytes("test", "sample.txt", secret.encode())
        self.assertIn("secret", {item["category"] for item in findings})
        self.assertNotIn(secret, json.dumps(findings))

    def test_email_examples_and_real_candidates(self):
        self.assertEqual(self.categories(b"fixture@sub.example.org noreply@github.com"), set())
        address = "fixture@" + "private-mail.test-domain.com"
        self.assertIn("email-address", self.categories(address.encode()))

    def test_environment_filenames_are_checked(self):
        self.assertIn("environment-file", self.categories(b"", ".env.production"))
        self.assertNotIn("environment-file", self.categories(b"", ".env.example"))
        self.assertIn("local-only-file", self.categories(b"", "do-not-upload/local/backup.txt"))

    def test_literal_credentials_are_detected(self):
        value = "postgresql://fixture:" + "not-a-real-password" + "@localhost/db"
        self.assertIn("credential-url", self.categories(value.encode()))
        self.assertEqual(self.categories(b"postgresql://${DB_USER}:${DB_PASSWORD}@db/app"), set())


class PrivacyGitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="privacy-test-", dir=ROOT / "do-not-upload/scripts")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "--quiet")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@example.com", "-c", "commit.gpgsign=false", *args],
            stderr=subprocess.PIPE,
        )

    def test_reads_staged_blob_even_after_working_copy_is_cleaned(self):
        p = self.repo / "sample.txt"
        p.write_text("sk-" + "b" * 35)
        self.git("add", "sample.txt")
        p.write_text("safe sample")
        findings = scanner.scan_repo(self.repo)["findings"]
        self.assertTrue(any(f["scope"] == "index" and f["category"] == "secret" for f in findings))
        self.assertFalse(any(f["scope"] == "worktree" for f in findings))

    def test_reads_staged_blob_after_file_is_deleted(self):
        p = self.repo / "sample.txt"
        p.write_text("sk-" + "c" * 35)
        self.git("add", "sample.txt")
        p.unlink()
        self.assertTrue(any(f["scope"] == "index" for f in scanner.scan_repo(self.repo)["findings"]))

    def test_scans_untracked_but_respects_ignored_runtime_files(self):
        (self.repo / ".gitignore").write_text("local-only.txt\n")
        for name in ("untracked.txt", "local-only.txt"):
            (self.repo / name).write_text("sk-" + "d" * 35)
        findings = scanner.scan_repo(self.repo)["findings"]
        self.assertTrue(any(f["path"] == "untracked.txt" for f in findings))
        self.assertFalse(any(f["path"] == "local-only.txt" for f in findings))

    def test_detects_removed_file_in_history(self):
        (self.repo / "cache.pyc").write_bytes(b"\0" + ("/Users/" + "fixture-user/code.py").encode())
        self.git("add", "cache.pyc")
        self.git("commit", "--quiet", "-m", "fixture")
        self.git("rm", "--quiet", "cache.pyc")
        self.git("commit", "--quiet", "-m", "remove fixture")
        findings = scanner.scan_repo(self.repo, history_only=True)["findings"]
        self.assertTrue(any(f["scope"] == "history" and f["category"] == "personal-path" for f in findings))

    def test_detects_forbidden_filename_when_blob_content_is_shared(self):
        (self.repo / "safe.txt").write_text("safe")
        (self.repo / ".env").write_text("safe")
        self.git("add", "safe.txt", ".env")
        self.git("commit", "--quiet", "-m", "fixture")
        findings = scanner.scan_repo(self.repo, history_only=True)["findings"]
        self.assertTrue(any(f["path"] == ".env" and f["category"] == "environment-file" for f in findings))

    def test_internal_tree_snapshot_does_not_count_as_branch_history(self):
        (self.repo / "cache.pyc").write_text("fixture")
        self.git("add", "cache.pyc")
        tree = self.git("write-tree").decode().strip()
        self.git("update-ref", "refs/codex/test", tree)
        result = scanner.scan_repo(self.repo, history_only=True)
        self.assertEqual(result["counts"]["history"], 0)
        self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
