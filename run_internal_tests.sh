#!/bin/bash
# Internal tests without starting the API server

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export TEST_MODE=true
export DATABASE_URL="sqlite:///./do-not-upload/data/test_internal.db"

echo "=========================================="
echo "Internal Testing Started"
echo "=========================================="

echo "Running unit tests..."
python3 -m pytest tests/unit/test_error_handling.py -v --tb=short -c tests/pytest.ini || true

echo ""
echo "Running feedback service tests..."
python3 -m pytest tests/unit/test_feedback_service.py -v --tb=short -c tests/pytest.ini || true

echo ""
echo "Running settings tests..."
python3 -m pytest tests/unit/test_settings.py -v --tb=short -c tests/pytest.ini || true

echo ""
echo "Done."
