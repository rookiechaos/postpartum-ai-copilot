#!/usr/bin/env python3
"""Check repository content for privacy risks without printing matched values.

Default scope: tracked and unignored working files, staged blobs, and all local
branches/tags. Use --history-only --repo PATH to inspect a fetched bare mirror.
Ignored runtime files and unreachable Git objects are outside this scope.
"""

import argparse
import hashlib
import ipaddress
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


HOME_PATH = re.compile(
    r"(?:/Users/|/home/)(?=[A-Za-z0-9._-]*[A-Za-z0-9])[A-Za-z0-9._-]+"
    r"|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+"
)
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
IPV6 = re.compile(r"(?<![\w:])(?:[0-9A-Fa-f]{0,4}:){2,}[0-9A-Fa-f:.]*(?![\w:])")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRETS = re.compile(
    r"sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}"
    r"|AIza[0-9A-Za-z_-]{30,}"
    r"|(?:AKIA|ASIA)[A-Z0-9]{16}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{40,}"
    r"|xox[baprs]-[A-Za-z0-9-]{15,}"
    r"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    r"|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
)
CREDENTIAL_URL = re.compile(
    r"(?:https?|postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
    r"([^\s/\"']+):([^\s/@\"']+)@"
)
ENV_SECRET = re.compile(
    r"(?m)^\s*(?:export\s+)?[A-Z][A-Z0-9_]*"
    r"(?:KEY|SECRET|TOKEN|PASSWORD)\s*=\s*[\"']?([^\s\"'#]+)"
)
EXAMPLE_NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32",
))
EXAMPLE_DOMAINS = {"example.com", "example.org", "example.net"}
EXAMPLE_SECRETS = {
    "sk-ant-your-api-key-here", "sk-your-api-key-here",
    "your-openai-api-key", "your-anthropic-api-key", "your-google-api-key",
    "your-secret-key-change-this-in-production",
    "your-secure-random-secret-key-here",
    "change-me-in-production-please-use-strong-random-key",
    "your_openai_api_key_here", "your_anthropic_api_key_here",
    "your_google_api_key_here", "your_stripe_webhook_secret_here",
    "your_secret_key_here_generate_with_openssl_rand_hex_32",
    "your-google-api-key-here", "your_key_here", "your_secret_key_here",
    "your_openai_key", "your_anthropic_key", "your_google_key",
    "generate_with_openssl_rand_hex_32", "test_secret_key",
    "test-secret-key-for-testing-only-32-chars-min", "TestPassword123!",
    "change-me", "password", "test", "", "...",
}
LOCAL_AREAS = {"data", "logs", "vector_db", "private-docs", "scripts", "local"}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def is_example_secret(value):
    return value in EXAMPLE_SECRETS or value.startswith(("${", "$", "<"))


def is_example_email(value):
    domain = value.rsplit("@", 1)[1].lower()
    return (
        any(domain == item or domain.endswith("." + item) for item in EXAMPLE_DOMAINS)
        or domain.endswith((".invalid", ".example"))
        or domain == "users.noreply.github.com"
        or value.lower() == "noreply@github.com"
    )


def is_example_ip(value):
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return True
    return (
        address.is_loopback or address.is_unspecified
        or any(address.version == net.version and address in net for net in EXAMPLE_NETWORKS)
    )


def forbidden_path(name):
    path = PurePosixPath(name)
    if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
        return "compiled-python"
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return "environment-file"
    if path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".log", ".p12", ".pfx"}:
        return "runtime-or-credential-file"
    if path.name in {"id_rsa", "id_ed25519", ".DS_Store"}:
        return "private-or-local-file"
    if len(path.parts) >= 3 and path.parts[0] == "do-not-upload" and path.parts[1] in LOCAL_AREAS:
        if path.name == ".gitkeep" or name == "do-not-upload/local/backend.env.example":
            return None
        return "local-only-file"
    return None


def scan_bytes(scope, path, data):
    text = data.decode("utf-8", errors="replace")
    findings = []

    def add(category, value, position=0):
        findings.append({
            "scope": scope, "path": path,
            "line": text.count("\n", 0, position) + 1,
            "category": category,
            "fingerprint": hashlib.sha256(value.encode()).hexdigest()[:12],
        })

    category = forbidden_path(path)
    if category:
        add(category, path)
    for rule, category in ((HOME_PATH, "personal-path"), (IPV4, "ip-address"),
                           (IPV6, "ip-address"), (EMAIL, "email-address"),
                           (SECRETS, "secret"), (ENV_SECRET, "secret-assignment")):
        for match in rule.finditer(text):
            value = match.group(1) if rule is ENV_SECRET else match.group()
            if category == "ip-address" and is_example_ip(value):
                continue
            if category == "email-address" and is_example_email(value):
                continue
            if category in {"secret", "secret-assignment"} and is_example_secret(value):
                continue
            if rule is ENV_SECRET and value == "re.compile(":
                continue
            add(category, value, match.start())
    for match in CREDENTIAL_URL.finditer(text):
        if "${" not in match.group() and not is_example_secret(match.group(2)):
            add("credential-url", match.group(), match.start())
    for match in HOME_PATH.finditer(path):
        add("personal-path-in-filename", match.group())
    return findings


def read_blobs(repo, entries):
    """Read Git objects, including staged files missing from the working tree."""
    if not entries:
        return []
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch"],
        input=b"".join(oid.encode() + b"\n" for oid, _ in entries),
        capture_output=True, check=True,
    ).stdout
    offset = 0
    blobs = []
    for _, path in entries:
        end = result.index(b"\n", offset)
        header = result[offset:end].split()
        if len(header) != 3:
            raise ValueError("Cannot read a referenced Git object")
        size = int(header[2])
        offset = end + 1
        if header[1] == b"blob":
            blobs.append((path, result[offset:offset + size]))
        offset += size + 1
    return blobs


def scan_repo(repo, history_only=False):
    findings = []
    counts = {}

    def scan(scope, entries):
        counts[scope] = len(entries)
        for name, data in entries:
            findings.extend(scan_bytes(scope, name, data))

    if not history_only:
        names = set(git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0"))
        files = []
        for raw in sorted(names - {b""}):
            name = raw.decode("utf-8", errors="surrogateescape")
            path = repo / name
            if path.is_symlink():
                files.append((name, str(path.readlink()).encode()))
            elif path.is_file():
                files.append((name, path.read_bytes()))
        scan("worktree", files)
        index = []
        for entry in git(repo, "ls-files", "--stage", "-z").split(b"\0"):
            if entry:
                meta, name = entry.split(b"\t", 1)
                mode, oid, _ = meta.decode().split()
                if mode == "160000":
                    findings.append({"scope": "index", "path": name.decode(), "line": 1,
                                     "category": "unscanned-submodule", "fingerprint": oid[:12]})
                else:
                    index.append((oid, name.decode("utf-8", errors="surrogateescape")))
        scan("index", read_blobs(repo, index))
    refs = git(repo, "for-each-ref", "--format=%(refname)",
               "refs/heads", "refs/tags", "refs/remotes").splitlines()
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"], capture_output=True)
    if refs or head.returncode == 0:
        head_args = ["HEAD"] if head.returncode == 0 else []
        revisions = [ref.decode() for ref in refs] + head_args
        entries = []
        for line in git(repo, "rev-list", "--objects", *revisions).splitlines():
            oid, _, name = line.partition(b" ")
            entries.append((oid.decode(), name.decode("utf-8", errors="surrogateescape")))
        scan("history", read_blobs(repo, entries))
        metadata = git(repo, "log", *revisions, "--format=%H%n%an <%ae>%n%cn <%ce>%n%B")
        scan("commit-metadata", [("commit-metadata", metadata)])
        # Content-identical files can have multiple historical names.
        names = set(git(repo, "log", *revisions, "--format=", "--name-only", "-z").split(b"\0"))
        for raw in names - {b""}:
            name = raw.decode("utf-8", errors="replace").strip("\n")
            if forbidden_path(name):
                findings.extend(scan_bytes("history-path", name, b""))
    else:
        counts["history"] = 0
    unique = {(f["scope"], f["path"], f["line"], f["category"], f["fingerprint"]): f for f in findings}
    return {"counts": counts, "findings": sorted(unique.values(), key=lambda f: (f["scope"], f["path"], f["line"], f["category"]))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--history-only", action="store_true", help="Scan all reachable branches/tags in a bare mirror")
    parser.add_argument("--json", action="store_true", help="Output counts and redacted finding locations as JSON")
    args = parser.parse_args()
    try:
        result = scan_repo(args.repo.resolve(), args.history_only)
    except (OSError, ValueError, subprocess.CalledProcessError):
        print("Privacy scan could not complete; no clean result is available.", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print("Scanned: " + ", ".join(f"{scope}={count}" for scope, count in result["counts"].items()))
        for item in result["findings"]:
            print(f"FAIL [{item['scope']}] {item['path']}:{item['line']} {item['category']} (value withheld)")
        print("Privacy scan failed; review the findings." if result["findings"] else "Privacy scan passed for the scanned scope.")
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
