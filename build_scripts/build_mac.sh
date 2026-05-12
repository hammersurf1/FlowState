#!/bin/bash
# ============================================================
#  FlowState — macOS Build Script
#  Compiles main_mac.py into a standalone .app bundle and
#  packages it into a .dmg installer using Apple's hdiutil.
#
#  Prerequisites:
#    - Python 3 with pip
#    - PyInstaller:  pip install pyinstaller
#    - All dependencies:  pip install -r requirements_mac.txt
# ============================================================

set -e

echo "Building FlowState for macOS..."

cd "$(dirname "$0")/.."

# 1. Compile Python to a standalone .app bundle
echo "[Step 1/2] Building .app with PyInstaller..."
pyinstaller \
    --windowed \
    --onefile \
    --name="FlowState" \
    --icon="assets/logo.png" \
    --hidden-import settings_gui \
    --collect-all playwright \
    src/main_mac.py

# 2. Package into a .dmg installer
echo "[Step 2/2] Creating .dmg installer..."
if [ -f "dist/FlowState_Mac_Installer.dmg" ]; then
    rm "dist/FlowState_Mac_Installer.dmg"
fi

hdiutil create \
    -volname "FlowState" \
    -srcfolder dist/FlowState.app \
    -ov \
    -format UDZO \
    dist/FlowState_Mac_Installer.dmg

echo ""
echo "Done! Check the 'dist' folder for FlowState_Mac_Installer.dmg"
