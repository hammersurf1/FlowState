@echo off
REM ============================================================
REM  FlowState — Windows Build Script
REM  Compiles main_win.py into a standalone directory bundle
REM  and packages it into a branded installer using Inno Setup.
REM
REM  Prerequisites:
REM    - Python 3.10+ with pip
REM    - PyInstaller:  pip install pyinstaller
REM    - All dependencies:  pip install -r requirements_win.txt
REM    - Inno Setup 6:  https://jrsoftware.org/isinfo.php
REM ============================================================

echo.
echo  =============================================
echo   FlowState — Windows Build
echo  =============================================
echo.

cd /d "%~dp0\.."

REM ── Step 1: Read version from pyproject.toml ──────────────────
for /f "tokens=3 delims= '\"" %%v in ('findstr /R "^version" pyproject.toml') do set APP_VERSION=%%v
echo Version: %APP_VERSION%

REM ── Step 2: Sync version.py ───────────────────────────────────
echo __version__ = "%APP_VERSION%" > src\version.py
echo Synced src\version.py to %APP_VERSION%
echo.

REM ── Step 3: Clean previous builds ────────────────────────────
echo [Step 1/3] Cleaning previous builds...
if exist dist\FlowState rmdir /s /q dist\FlowState
if exist build\FlowState rmdir /s /q build\FlowState
echo   OK
echo.

REM ── Step 4: Build with PyInstaller (onedir mode) ─────────────
echo [Step 2/3] Building with PyInstaller (onedir)...
pyinstaller FlowState.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: PyInstaller build failed.
    pause
    exit /b 1
)
echo   OK
echo.

REM ── Step 5: Create Installer with Inno Setup ────────────────
echo [Step 3/3] Creating Windows Installer with Inno Setup...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build_scripts\windows_setup.iss
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Inno Setup compilation failed.
    pause
    exit /b 1
)
echo   OK
echo.

echo  =============================================
echo   Build complete!
echo  =============================================
echo.
echo  Output: dist\FlowState_Windows_Setup.exe
echo.
echo  NOTE: This installer is not code-signed.
echo  Users may see a Windows SmartScreen warning.
echo  They should click "More info" then "Run anyway".
echo.
pause