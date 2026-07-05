"""Bootstrap backend imports for worker processes."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


def setup_backend_path() -> Path:
    """Add backend/ to sys.path so services and models can be imported."""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    return BACKEND_DIR
