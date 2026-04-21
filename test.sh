#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR=".venv"

echo "🧪 Hotel Dispatcher — Test Suite"
echo "=================================="
echo ""

# Activate venv
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found. Run ./run.sh first."
    exit 1
fi

source "$VENV_DIR/bin/activate"

echo "Running pytest..."
pytest tests/ -v --tb=short

echo ""
echo "✅ All tests passed!"
