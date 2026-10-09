"""Bootstrap backend and core imports for worker processes."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
CORE_DIR = PROJECT_ROOT / "core"


def setup_backend_path() -> Path:
    """Add core/ and backend/ to sys.path."""
    for directory in (CORE_DIR, BACKEND_DIR):
        path = str(directory)
        if path not in sys.path:
            sys.path.insert(0, path)
    return BACKEND_DIR
