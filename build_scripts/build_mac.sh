#!/bin/bash
# ============================================================
#  FlowState — macOS Build Script
#  Compiles main_mac.py into a standalone .app bundle and
#  packages it into a branded .dmg installer.
#
#  Prerequisites:
#    - Python 3.10+ with pip
#    - PyInstaller:  pip install pyinstaller
#    - All dependencies:  pip install -r requirements_mac.txt
#    - create-dmg:  brew install create-dmg
# ============================================================

set -e

echo ""
echo " ============================================="
echo "  FlowState — macOS Build"
echo " ============================================="
echo ""

cd "$(dirname "$0")/.."

# ── Step 1: Read version from pyproject.toml ──────────────────
APP_VERSION=$(python3 -c "import re; print(re.search(r'version\s*=\s*\"(.+?)\"', open('pyproject.toml').read()).group(1))")
echo "Version: $APP_VERSION"

# ── Step 2: Sync version.py ───────────────────────────────────
echo "__version__ = \"$APP_VERSION\"" > src/version.py
echo "Synced src/version.py to $APP_VERSION"
echo ""

# ── Step 3: Clean previous builds ────────────────────────────
echo "[Step 1/3] Cleaning previous builds..."
rm -rf dist/FlowState dist/FlowState.app build/FlowState
echo "  OK"
echo ""

# ── Step 4: Build .app bundle with PyInstaller ────────────────
echo "[Step 2/3] Building .app with PyInstaller..."
pyinstaller FlowState_mac.spec --clean --noconfirm
echo "  OK"
echo ""

# ── Step 5: Create branded DMG ────────────────────────────────
echo "[Step 3/3] Creating branded DMG installer..."
if [ -f "dist/FlowState_Mac_Installer.dmg" ]; then
    rm "dist/FlowState_Mac_Installer.dmg"
fi

# Check if create-dmg is available
if command -v create-dmg &> /dev/null; then
    create-dmg \
        --volname "FlowState" \
        --volicon "assets/logo.icns" \
        --background "assets/installer/dmg_background.png" \
        --window-pos 200 120 \
        --window-size 660 400 \
        --icon-size 80 \
        --icon "FlowState.app" 180 200 \
        --app-drop-link 480 200 \
        --hide-extension "FlowState.app" \
        --no-internet-enable \
        "dist/FlowState_Mac_Installer.dmg" \
        "dist/FlowState.app" || true
else
    echo "  create-dmg not found, falling back to hdiutil..."
    echo "  (Install create-dmg for a branded DMG: brew install create-dmg)"
    hdiutil create \
        -volname "FlowState" \
        -srcfolder dist/FlowState.app \
        -ov \
        -format UDZO \
        dist/FlowState_Mac_Installer.dmg
fi

echo "  OK"
echo ""

# ── Optional: Sign & Notarize ─────────────────────────────────
if [ -n "$APPLE_SIGNING_IDENTITY" ]; then
    echo "[Optional] Signing with Developer ID..."
    codesign --deep --force --options=runtime \
        --entitlements build_scripts/entitlements.plist \
        --sign "$APPLE_SIGNING_IDENTITY" --timestamp \
        "dist/FlowState.app"

    if [ -n "$APPLE_NOTARY_PROFILE" ]; then
        echo "Submitting for notarization..."
        ditto -c -k --keepParent "dist/FlowState.app" "/tmp/FlowState_notarize.zip"
        xcrun notarytool submit "/tmp/FlowState_notarize.zip" \
            --keychain-profile "$APPLE_NOTARY_PROFILE" --wait
        xcrun stapler staple "dist/FlowState.app"
        rm "/tmp/FlowState_notarize.zip"
    fi
fi

echo " ============================================="
echo "  Build complete!"
echo " ============================================="
echo ""
echo " Output: dist/FlowState_Mac_Installer.dmg"
echo ""
echo " NOTE: This app is not notarized."
echo " Users may need to right-click > Open on first launch,"
echo " or run: xattr -cr /Applications/FlowState.app"
echo ""
