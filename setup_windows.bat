@echo off
REM ============================================================
REM  FlowState — Windows Manual Setup
REM  This script sets up a local Python environment and installs
REM  all dependencies needed to run FlowState on Windows.
REM
REM  WHAT THIS SCRIPT DOES (nothing hidden):
REM    1. Checks that Python 3 is installed
REM    2. Creates a virtual environment in .venv\
REM    3. Installs Python packages from requirements_win.txt
REM    4. Prints instructions for how to run FlowState
REM
REM  WHAT THIS SCRIPT DOES NOT DO:
REM    - It does NOT install anything system-wide
REM    - It does NOT modify your registry
REM    - It does NOT require admin rights (but running FlowState does)
REM ============================================================

echo.
echo  =============================================
echo   FlowState — Windows Setup
echo  =============================================
echo.

REM ── Step 1: Check Python ──────────────────────────────────────
echo [Step 1/3] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not on your PATH.
    echo  Please install Python 3.10+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
python --version
echo   OK
echo.

REM ── Step 2: Create Virtual Environment ────────────────────────
echo [Step 2/3] Creating virtual environment in .venv\ ...
if exist .venv (
    echo   .venv already exists, skipping creation.
) else (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)
echo   OK
echo.

REM ── Step 3: Install Dependencies ─────────────────────────────
echo [Step 3/3] Installing dependencies from requirements_win.txt...
call .venv\Scripts\activate.bat
pip install -r requirements_win.txt
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: pip install failed. Check the output above for details.
    pause
    exit /b 1
)
echo   OK
echo.

REM ── Done ─────────────────────────────────────────────────────
echo  =============================================
echo   Setup complete!
echo  =============================================
echo.
echo  To run FlowState:
echo.
echo    1. Open a Command Prompt AS ADMINISTRATOR
echo       (Right-click Command Prompt ^> "Run as administrator")
echo.
echo    2. Navigate to this folder:
echo       cd %cd%
echo.
echo    3. Activate the virtual environment:
echo       .venv\Scripts\activate
echo.
echo    4. Start FlowState:
echo       python src\main_win.py
echo.
echo  NOTE: Administrator is required because FlowState uses global
echo  keyboard hooks to detect hotkeys like Ctrl+Alt+V. This is a
echo  Windows security requirement, not a FlowState choice.
echo.
pause
