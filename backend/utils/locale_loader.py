"""
Locale loader - Load user-facing localized content from JSON files.
Keeps Python source code English-only while supporting runtime i18n.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

LOCALES_DIR = Path(__file__).resolve().parent.parent.parent / "locales"


@lru_cache(maxsize=32)
def load_locale_file(language: str, name: str) -> Dict[str, Any]:
    """Load a JSON locale file by language code and file name (without extension)."""
    path = LOCALES_DIR / language / f"{name}.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_locale_text(language: str, name: str) -> Optional[str]:
    """Load a plain-text locale file."""
    path = LOCALES_DIR / language / f"{name}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def get_localized_value(
    data: Dict[str, Any],
    language: str,
    fallback_language: str = "en",
) -> Any:
    """Return localized value from a dict keyed by language code."""
    if language in data:
        return data[language]
    return data.get(fallback_language, data.get("en"))
