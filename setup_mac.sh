#!/bin/bash
# ============================================================
#  FlowState — macOS Manual Setup
#  This script sets up a local Python environment and installs
#  all dependencies needed to run FlowState on macOS.
#
#  WHAT THIS SCRIPT DOES (nothing hidden):
#    1. Checks that Python 3 is installed
#    2. Creates a virtual environment in .venv/
#    3. Installs Python packages from requirements_mac.txt
#    4. Prints instructions for how to run FlowState
#
#  WHAT THIS SCRIPT DOES NOT DO:
#    - It does NOT install anything system-wide
#    - It does NOT require sudo or root access
#    - It does NOT modify system preferences
# ============================================================

set -e

echo ""
echo " ============================================="
echo "  FlowState — macOS Setup"
echo " ============================================="
echo ""

# ── Step 1: Check Python ──────────────────────────────────────
echo "[Step 1/3] Checking for Python 3..."
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
echo ""

# ── Step 2: Create Virtual Environment ────────────────────────
echo "[Step 2/3] Creating virtual environment in .venv/ ..."
if [ -d ".venv" ]; then
    echo "  .venv already exists, skipping creation."
else
    python3 -m venv .venv
fi
echo "  OK"
echo ""

# ── Step 3: Install Dependencies ─────────────────────────────
echo "[Step 3/3] Installing dependencies from requirements_mac.txt..."
source .venv/bin/activate
pip install -r requirements_mac.txt
echo "  OK"
echo ""

# ── Done ─────────────────────────────────────────────────────
echo " ============================================="
echo "  Setup complete!"
echo " ============================================="
echo ""
echo " IMPORTANT — Grant Accessibility Permission:"
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
echo "   1. Open Terminal"
echo "   2. Navigate to this folder:"
echo "      cd $(pwd)"
echo "   3. Activate the virtual environment:"
echo "      source .venv/bin/activate"
echo "   4. Start FlowState:"
echo "      python3 src/main_mac.py"
echo ""
