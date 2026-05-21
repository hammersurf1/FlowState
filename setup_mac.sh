#!/bin/bash
# ============================================================
#  FlowState - macOS Manual Setup
#  This script sets up a local Python environment and installs
#  all dependencies needed to run FlowState on macOS.
#
#  WHAT THIS SCRIPT DOES (nothing hidden):
#    1. Checks for uv or Python 3
#    2. Creates a virtual environment in .venv/
#    3. Installs Python packages from requirements_mac.txt
#    4. Downloads the spaCy language model
#    5. Prints instructions for how to run FlowState
#
#  WHAT THIS SCRIPT DOES NOT DO:
#    - It does NOT install anything system-wide
#    - It does NOT require sudo or root access
#    - It does NOT modify system preferences
# ============================================================

set -e

echo ""
echo " ============================================="
echo "  FlowState - macOS Setup"
echo " ============================================="
echo ""

# --- Detect uv ------------------------------------------------
USE_UV=0
if command -v uv &> /dev/null; then
    USE_UV=1
    echo "  [uv detected - using uv for fast install]"
    echo ""
fi

# --- Step 1: Check Python --------------------------------------
echo "[Step 1/4] Checking for Python 3..."

if [ "$USE_UV" -eq 1 ]; then
    if uv python find &> /dev/null; then
        echo "  OK"
    else
        echo "  No Python found, uv will download one automatically."
    fi
else
    if ! command -v python3 &> /dev/null; then
        echo ""
        echo "  ERROR: Python 3 is not installed."
        echo "  Install it with Homebrew:  brew install python"
        echo "  Or download from:         https://www.python.org/downloads/"
        echo ""
        exit 1
    fi
    python3 --version
    echo "  OK"
fi
echo ""

# --- Step 2: Create Virtual Environment -------------------------
echo "[Step 2/4] Creating virtual environment in .venv/ ..."
if [ -d ".venv" ]; then
    echo "  .venv already exists, skipping creation."
else
    if [ "$USE_UV" -eq 1 ]; then
        uv venv .venv
    else
        python3 -m venv .venv
    fi
fi
echo "  OK"
echo ""

# --- Step 3: Install Dependencies ------------------------------
echo "[Step 3/4] Installing dependencies from requirements_mac.txt..."
if [ "$USE_UV" -eq 1 ]; then
    uv pip install -r requirements_mac.txt
else
    source .venv/bin/activate
    pip install -r requirements_mac.txt
fi
echo "  OK"
echo ""

# --- Step 4: Download spaCy Model -----------------------------
echo "[Step 4/4] Downloading spaCy language model (en_core_web_md)..."
if [ "$USE_UV" -eq 1 ]; then
    uv run python -m spacy download en_core_web_md
else
    python3 -m spacy download en_core_web_md
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
