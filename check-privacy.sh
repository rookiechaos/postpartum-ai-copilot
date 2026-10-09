#!/bin/bash
# Scan publishable files, the actual Git index, and reachable history.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/scripts/privacy_scan.py" "$@"
