#!/bin/bash
# ============================================================
#  FlowState - macOS Manual Setup
#  Enforces Python 3.11-3.12 (spaCy has no wheels for 3.13+).
#  If the wrong version is found, the script installs 3.12
#  automatically (via uv if available) or prompts for manual install.
# ============================================================

set -e

echo ""
echo " ============================================="
echo "  FlowState - macOS Setup"
echo " ============================================="
echo ""

# --- Constants ------------------------------------------------
PY_MAJOR=3
PY_MINOR=12
PY_VER="${PY_MAJOR}.${PY_MINOR}"

# --- Detect uv ------------------------------------------------
USE_UV=0
if command -v uv &> /dev/null; then
    USE_UV=1
    echo "  [uv detected - using uv for fast install]"
    echo ""
fi

# --- Helper: parse version from "Python 3.12.x" ---------------
parse_python_version() {
    local cmd="$1"
    local ver_str
    ver_str=$("$cmd" --version 2>&1)
    echo "$ver_str" | awk '{print $2}'
}

# --- Helper: check if version is acceptable -------------------
is_version_acceptable() {
    local ver="$1"
    local maj min
    maj=$(echo "$ver" | cut -d. -f1)
    min=$(echo "$ver" | cut -d. -f2)

    if [ "$maj" -ne 3 ]; then
        return 1
    fi
    if [ "$min" -lt 11 ] || [ "$min" -gt 12 ]; then
        return 1
    fi
    return 0
}

# --- Step 0: Enforce Python 3.12 -----------------------------
echo "[Step 0/5] Ensuring Python ${PY_VER} is available..."
PYTHON_CMD=""

if [ "$USE_UV" -eq 1 ]; then
    # uv can manage its own Python. Check if 3.12 is already installed.
    if uv python find "$PY_VER" &> /dev/null; then
        echo "  uv-managed Python ${PY_VER} found."
        PYTHON_CMD="$(uv python find "$PY_VER")"
    else
        echo "  Installing Python ${PY_VER} via uv (this may take a moment)..."
        uv python install "$PY_VER"
        PYTHON_CMD="$(uv python find "$PY_VER")"
    fi
else
    # Check python3, python, py in order
    for candidate in python3 python py; do
        if command -v "$candidate" &> /dev/null; then
            ver=$(parse_python_version "$candidate")
            if is_version_acceptable "$ver"; then
                PYTHON_CMD="$candidate"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        echo ""
        echo "  ERROR: No suitable Python found."
        echo ""
        echo "  FlowState requires Python 3.11 or 3.12."
        echo "  spaCy does not yet provide pre-built wheels for Python 3.13+."
        echo ""
        echo "  To install Python ${PY_VER}:"
        echo ""
        echo "    Option A - Homebrew (recommended):"
        echo "      brew install python@${PY_MINOR}"
        echo ""
        echo "    Option B - Official installer:"
        echo "      https://www.python.org/downloads/release/python-31210/"
        echo ""
        echo "    Option C - Install uv (handles Python automatically):"
        echo "      curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        exit 1
    fi
fi

echo "  OK  (${PYTHON_CMD})"
echo ""

# --- Step 1: Verify version (guard) ---------------------------
echo "[Step 1/5] Verifying Python version..."
RAW_VER=$(parse_python_version "$PYTHON_CMD")
echo "  Python ${RAW_VER}"

if ! is_version_acceptable "$RAW_VER"; then
    echo ""
    echo "  ERROR: Python ${RAW_VER} is not supported."
    echo "  Only Python 3.11 and 3.12 are supported (spaCy wheel availability)."
    echo ""
    exit 1
fi
echo "  OK  (Python ${RAW_VER} is supported)"
echo ""

# --- Step 2: Create Virtual Environment -------------------------
echo "[Step 2/5] Creating virtual environment in .venv/ ..."
if [ -d ".venv" ]; then
    echo "  .venv already exists, skipping creation."
else
    if [ "$USE_UV" -eq 1 ]; then
        uv venv --python "$PY_VER" .venv
    else
        "$PYTHON_CMD" -m venv .venv
    fi
fi
echo "  OK"
echo ""

# --- Step 3: Install Dependencies ------------------------------
echo "[Step 3/5] Installing dependencies from requirements_mac.txt..."
if [ "$USE_UV" -eq 1 ]; then
    uv pip install -r requirements_mac.txt
else
    source .venv/bin/activate
    pip install -r requirements_mac.txt
fi
echo "  OK"
echo ""

# --- Step 4: Download spaCy Model -----------------------------
echo "[Step 4/5] Downloading spaCy language model (en_core_web_md)..."
if [ "$USE_UV" -eq 1 ]; then
    uv pip install "https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.7.1/en_core_web_md-3.7.1.tar.gz"
else
    .venv/bin/pip install "https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.7.1/en_core_web_md-3.7.1.tar.gz"
fi
echo "  OK"
echo ""

# --- Done -----------------------------------------------------
echo " ============================================="
echo "  Setup complete!"
echo " ============================================="
echo ""
echo " IMPORTANT - Grant Accessibility Permission:"
echo ""
echo "   FlowState uses global keyboard shortcuts (⌘+⌥+V) to work."
echo "   macOS requires you to grant Accessibility access:"
echo ""
echo "     1. Open System Settings > Privacy & Security > Accessibility"
echo "     2. Click the + button and add your Terminal app"
echo "        (Terminal.app, iTerm2, or whichever you use)"
echo "     3. You only need to do this once"
echo ""

if [ "$USE_UV" -eq 1 ]; then
    echo " To run FlowState:"
    echo ""
    echo "   cd $(pwd)"
    echo "   uv run python3 src/main_mac.py"
    echo ""
else
    echo " To run FlowState:"
    echo ""
    echo "   1. Open Terminal"
    echo "   2. Navigate to this folder:"
    echo "      cd $(pwd)"
    echo "   3. Activate the virtual environment:"
    echo "      source .venv/bin/activate"
    echo "   4. Start FlowState:"
    echo "      python3 src/main_mac.py"
    echo ""
fi
