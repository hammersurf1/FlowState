#!/bin/bash
# ============================================================
#  FlowState - macOS Manual Setup
#  Requires uv. Enforces Python 3.11-3.12 via uv-managed Python.
# ============================================================

set -e

echo ""
echo " ============================================="
echo "  FlowState - macOS Setup"
echo " ============================================="
echo ""

PY_MAJOR=3
PY_MINOR=12
PY_VER="${PY_MAJOR}.${PY_MINOR}"

if ! command -v uv &> /dev/null; then
    echo "  ERROR: uv is required but was not found on PATH."
    echo ""
    echo "  Install uv, then re-run this script:"
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "  Or see: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "  [using uv for environment and dependencies]"
echo ""

parse_python_version() {
    local cmd="$1"
    local ver_str
    ver_str=$("$cmd" --version 2>&1)
    echo "$ver_str" | awk '{print $2}'
}

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

echo "[Step 0/5] Ensuring Python ${PY_VER} is available via uv..."
if uv python find "$PY_VER" &> /dev/null; then
    echo "  uv-managed Python ${PY_VER} found."
    PYTHON_CMD="$(uv python find "$PY_VER")"
else
    echo "  Installing Python ${PY_VER} via uv (this may take a moment)..."
    uv python install "$PY_VER"
    PYTHON_CMD="$(uv python find "$PY_VER")"
fi
echo "  OK  (${PYTHON_CMD})"
echo ""

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

echo "[Step 2/5] Creating virtual environment in .venv/ ..."
if [ -d ".venv" ]; then
    echo "  .venv already exists, skipping creation."
else
    uv venv --python "$PY_VER" .venv
fi
echo "  OK"
echo ""

echo "[Step 3/5] Installing dependencies from pyproject.toml (uv sync)..."
uv sync
echo "  OK"
echo ""

echo "[Step 4/5] Downloading spaCy model and NLTK WordNet corpora..."
uv run python scripts/download_models.py
echo "  OK"
echo ""

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
echo " To run FlowState:"
echo ""
echo "   cd $(pwd)"
echo "   uv run python3 src/main_mac.py"
echo ""
echo " To download/update language models later:"
echo "   uv run python scripts/download_models.py"
echo ""
