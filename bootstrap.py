"""Bootstrap Python path for backend + core packages."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
CORE_DIR = PROJECT_ROOT / "core"


def setup_python_path() -> tuple[Path, Path]:
    """Add core/ and backend/ to sys.path (core first for services imports)."""
    for directory in (CORE_DIR, BACKEND_DIR):
        path = str(directory)
        if path not in sys.path:
            sys.path.insert(0, path)
    return BACKEND_DIR, CORE_DIR
