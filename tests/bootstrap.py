"""Shared path setup for tests outside the backend package."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
CORE_DIR = PROJECT_ROOT / "core"

for directory in (CORE_DIR, BACKEND_DIR):
    path = str(directory)
    if path not in sys.path:
        sys.path.insert(0, path)
