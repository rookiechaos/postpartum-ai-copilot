"""Resolve private runtime storage independently of the process working directory."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = PROJECT_ROOT / "do-not-upload"


def resolve_runtime_path(value: str, default_directory: str) -> Path:
    """Keep logs and vector data inside the project's private runtime directory."""
    # Accept the previous defaults when upgrading existing local configurations.
    if value == f"../do-not-upload/{default_directory}":
        value = f"do-not-upload/{default_directory}"
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    try:
        resolved.relative_to(RUNTIME_ROOT.resolve())
    except ValueError:
        raise ValueError("Runtime storage must be inside do-not-upload") from None
    return resolved
