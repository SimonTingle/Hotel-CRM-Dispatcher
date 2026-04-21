#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR=".venv"
PYTHON_BIN=""
PYTHON_VERSION=""

echo "🏨 Hotel Dispatcher — Local Setup & Run"
echo "========================================"
echo ""

# ============================================================================
# FAILSAFE 1: Find compatible Python version (3.12 > 3.11)
# ============================================================================
find_python() {
    # Try python3.12 first (preferred)
    if command -v python3.12 &> /dev/null; then
        PYTHON_BIN="python3.12"
        PYTHON_VERSION=$(python3.12 --version 2>&1 | awk '{print $2}')
        echo "✓ Found Python $PYTHON_VERSION (python3.12)"
        return 0
    fi

    # Fallback to python3.11
    if command -v python3.11 &> /dev/null; then
        PYTHON_BIN="python3.11"
        PYTHON_VERSION=$(python3.11 --version 2>&1 | awk '{print $2}')
        echo "✓ Found Python $PYTHON_VERSION (python3.11)"
        return 0
    fi

    # Fallback to generic python3 (if compatible)
    if command -v python3 &> /dev/null; then
        local ver=$(python3 --version 2>&1 | awk '{print $2}')
        local major=$(echo "$ver" | cut -d'.' -f1)
        local minor=$(echo "$ver" | cut -d'.' -f2)

        if [ "$major" = "3" ] && ([ "$minor" = "11" ] || [ "$minor" = "12" ]); then
            PYTHON_BIN="python3"
            PYTHON_VERSION="$ver"
            echo "✓ Found Python $PYTHON_VERSION (python3)"
            return 0
        fi
    fi

    return 1
}

# ============================================================================
# FAILSAFE 2: Check for incompatible Python versions
# ============================================================================
if ! find_python; then
    echo "❌ No compatible Python found (need 3.11 or 3.12)"
    echo ""
    echo "Current Python versions available:"
    for cmd in python3.14 python3.13 python3.12 python3.11 python3; do
        if command -v "$cmd" &> /dev/null; then
            echo "  ✗ $cmd: $($cmd --version 2>&1)"
        fi
    done
    echo ""
    echo "📋 Install Python 3.12 with Homebrew:"
    echo "   brew install python@3.12"
    echo ""
    echo "📋 Or download from:"
    echo "   https://www.python.org/downloads/ (macOS 3.12.x)"
    echo ""
    echo "📋 After installing, try again:"
    echo "   rm -rf .venv && ./run.sh"
    exit 1
fi

# ============================================================================
# FAILSAFE 3: Validate Python version compatibility
# ============================================================================
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" != "3" ] || ([ "$PYTHON_MINOR" != "11" ] && [ "$PYTHON_MINOR" != "12" ]); then
    echo "❌ Python $PYTHON_VERSION is not compatible"
    echo "   Need Python 3.11 or 3.12 (pydantic-core restriction)"
    exit 1
fi

echo ""

# ============================================================================
# FAILSAFE 4: Check venv state and recreate if corrupted
# ============================================================================
if [ -d "$VENV_DIR" ]; then
    if ! [ -f "$VENV_DIR/bin/activate" ]; then
        echo "⚠️  Virtual environment corrupted (missing activate). Recreating..."
        rm -rf "$VENV_DIR"
    elif ! [ -f "$VENV_DIR/pyvenv.cfg" ]; then
        echo "⚠️  Virtual environment corrupted (missing pyvenv.cfg). Recreating..."
        rm -rf "$VENV_DIR"
    fi
fi

# ============================================================================
# FAILSAFE 5: Create or verify venv
# ============================================================================
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment with $PYTHON_BIN..."
    if ! $PYTHON_BIN -m venv "$VENV_DIR" 2>&1; then
        echo "❌ Failed to create venv. Possible causes:"
        echo "   - Disk space full"
        echo "   - Permission denied"
        echo "   - Python installation corrupted"
        exit 1
    fi
fi

# ============================================================================
# FAILSAFE 6: Activate venv and verify
# ============================================================================
echo "🔌 Activating virtual environment..."
if ! source "$VENV_DIR/bin/activate" 2>&1; then
    echo "❌ Failed to activate venv"
    exit 1
fi

# Verify we're in the venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to enter virtual environment"
    exit 1
fi

echo "   ✓ Activated: $VIRTUAL_ENV"

# ============================================================================
# FAILSAFE 7: Upgrade pip with retry logic
# ============================================================================
echo "⬆️  Upgrading pip, setuptools, wheel..."
for attempt in 1 2 3; do
    if pip install --quiet --upgrade pip setuptools wheel 2>&1; then
        echo "   ✓ pip upgraded"
        break
    else
        if [ $attempt -lt 3 ]; then
            echo "   ⚠️  Attempt $attempt failed, retrying..."
            sleep 2
        else
            echo "❌ Failed to upgrade pip after 3 attempts"
            exit 1
        fi
    fi
done

# ============================================================================
# FAILSAFE 8: Install dependencies with comprehensive error handling
# ============================================================================
echo "📚 Installing dependencies from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found"
    exit 1
fi

for attempt in 1 2; do
    if pip install -r requirements.txt 2>&1 | tee /tmp/pip_install.log; then
        echo "   ✓ Dependencies installed"
        break
    else
        if [ $attempt -lt 2 ]; then
            echo "   ⚠️  Installation failed on attempt 1, checking logs..."

            # Check for specific failure reasons
            if grep -q "pydantic-core" /tmp/pip_install.log; then
                echo "   ❌ Pydantic-core failed to build (incompatible Python)"
                echo "   Make sure you're using Python 3.11 or 3.12 exactly"
                exit 1
            fi

            # Clear pip cache and retry
            echo "   Clearing pip cache and retrying..."
            pip cache purge --quiet 2>/dev/null || true
            sleep 2
        else
            echo "❌ Failed to install dependencies"
            echo "   Check /tmp/pip_install.log for details"
            exit 1
        fi
    fi
done

# ============================================================================
# FAILSAFE 9: Verify critical packages installed
# ============================================================================
echo "✅ Verifying critical packages..."
for pkg in fastapi pydantic redis supabase; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        echo "❌ Package '$pkg' failed to import"
        exit 1
    fi
done
echo "   ✓ All critical packages verified"

# ============================================================================
# FAILSAFE 10: Setup .env file with safety checks
# ============================================================================
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.local.example..."
    if [ -f ".env.local.example" ]; then
        cp .env.local.example .env
        echo "   ✓ .env created (TEST_MODE=true)"
    elif [ -f ".env.example" ]; then
        echo "⚠️  Using .env.example (not ideal for local)"
        cp .env.example .env
    else
        echo "❌ No .env template found"
        exit 1
    fi
else
    # Verify .env doesn't have production secrets
    if grep -q "sk_live\|sk_test\|rk_live" .env 2>/dev/null; then
        echo "⚠️  WARNING: .env appears to contain production secrets!"
        echo "   This is only safe if running on a local machine"
        read -p "   Continue? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# ============================================================================
# FAILSAFE 11: Syntax check all Python files
# ============================================================================
echo "✅ Checking Python syntax..."
SYNTAX_ERRORS=0
for pyfile in $(find app -name "*.py" 2>/dev/null); do
    if [ -f "$pyfile" ]; then
        if ! python3 -m py_compile "$pyfile" 2>/dev/null; then
            echo "   ❌ Syntax error in $pyfile"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        fi
    fi
done

if [ $SYNTAX_ERRORS -gt 0 ]; then
    echo "❌ Found $SYNTAX_ERRORS syntax error(s)"
    exit 1
fi
echo "   ✓ All files passed syntax check"

# ============================================================================
# FAILSAFE 12: Port availability check
# ============================================================================
echo "✅ Checking port 8000 availability..."
if command -v lsof &> /dev/null; then
    if lsof -Pi :8000 -sTCP:LISTEN -t &> /dev/null; then
        echo "⚠️  Port 8000 already in use"
        echo "   Kill it with: lsof -ti:8000 | xargs kill -9"
        exit 1
    fi
fi

# ============================================================================
# FAILSAFE 13: Final pre-flight checks
# ============================================================================
echo ""
echo "✅ Pre-flight checks:"
echo "   ✓ Python: $PYTHON_VERSION"
echo "   ✓ Venv: $VIRTUAL_ENV"
echo "   ✓ Dependencies: installed"
echo "   ✓ .env: configured"
echo "   ✓ Port 8000: available"
echo "   ✓ Syntax: all files valid"

# ============================================================================
# LAUNCH
# ============================================================================
echo ""
echo "========================================"
echo "🚀 Starting development server..."
echo "========================================"
echo "   Endpoint: http://localhost:8000"
echo "   Health:   http://localhost:8000/healthz"
echo "   Docs:     http://localhost:8000/docs"
echo "   Logs:     Below"
echo ""
echo "Press Ctrl+C to stop."
echo "========================================"
echo ""

# Run the dev server with error handling
if ! uvicorn app.main:app --reload --reload-dir app --port 8000 --host 0.0.0.0; then
    echo ""
    echo "❌ Server failed to start"
    echo "   Check the error messages above"
    exit 1
fi
