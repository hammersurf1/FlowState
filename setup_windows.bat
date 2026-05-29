@echo off
REM ============================================================
REM  FlowState - Windows Manual Setup
REM  Enforces Python 3.11-3.12 (spaCy has no wheels for 3.13+).
REM  If the wrong version is found, Python 3.12 is installed
REM  automatically and used for the remainder of the script.
REM ============================================================

echo.
echo  =============================================
echo   FlowState - Windows Setup
echo  =============================================
echo.

REM --- Constants ------------------------------------------------
set "PY_MAJOR=3"
set "PY_MINOR=12"
set "PY_VER=%PY_MAJOR%.%PY_MINOR%"
set "PY_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
set "PY_INSTALLER=%TEMP%\python-3.12.10-amd64.exe"
set "VER_FILE=%TEMP%\flowstate_pyver.txt"

REM --- Require uv ------------------------------------------------
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ERROR: uv is required but was not found on PATH.
    echo.
    echo   Install uv, then re-run this script:
    echo     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    echo   Or see: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)
echo  [using uv for environment and dependencies]
echo.

REM --- Step 0: Enforce Python 3.12 via uv -----------------------
echo [Step 0/5] Ensuring Python %PY_VER% is available via uv...
set PYTHON_CMD=
call :uv_ensure_python
if %errorlevel% neq 0 (
    echo   ERROR: uv failed to provide Python %PY_VER%.
    pause
    exit /b 1
)
goto :python_ok

REM --- uv: ensure Python is available ----------------------------
:uv_ensure_python
uv python find %PY_VER% >"%VER_FILE%" 2>nul
if %errorlevel% equ 0 (
    echo   uv-managed Python %PY_VER% found.
    set /p PYTHON_CMD=<"%VER_FILE%"
    exit /b 0
)
echo   Installing Python %PY_VER% via uv (this may take a moment)...
uv python install %PY_VER%
if %errorlevel% neq 0 exit /b 1
uv python find %PY_VER% >"%VER_FILE%"
set /p PYTHON_CMD=<"%VER_FILE%"
exit /b 0

REM --- non-uv: find system python ------------------------------
:find_system_python
REM Try py launcher with version flag first
py -%PY_VER% --version >"%VER_FILE%" 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -%PY_VER%"
    exit /b 0
)

REM Try python3, python, py and check versions
call :check_python_version python3
if not "%PYTHON_CMD%"=="" exit /b 0
call :check_python_version python
if not "%PYTHON_CMD%"=="" exit /b 0
call :check_python_version py
exit /b 0

:python_ok
echo   OK  ^(%PYTHON_CMD%^)
echo.

REM --- Step 1: Verify version (guard) ---------------------------
echo [Step 1/5] Verifying Python version...
%PYTHON_CMD% --version >"%VER_FILE%" 2>&1
set /p RAW_PY_VERSION=<"%VER_FILE%"
echo   %RAW_PY_VERSION%

for /f "tokens=2 delims= " %%a in ("%RAW_PY_VERSION%") do set "DETECTED_VER=%%a"
for /f "tokens=1,2 delims=." %%a in ("%DETECTED_VER%") do (
    set "DETECTED_MAJOR=%%a"
    set "DETECTED_MINOR=%%b"
)

if %DETECTED_MAJOR% neq 3 (
    echo   ERROR: Only Python 3.x is supported.
    pause
    exit /b 1
)
if %DETECTED_MINOR% lss 11 (
    echo   ERROR: Python %DETECTED_VER% is too old. Python 3.11+ required.
    pause
    exit /b 1
)
if %DETECTED_MINOR% gtr 12 (
    echo   ERROR: Python %DETECTED_VER% is too new. spaCy does not yet provide
    echo          pre-built wheels for Python 3.13+ on Windows. Please use 3.11 or 3.12.
    pause
    exit /b 1
)
echo   OK  ^(Python %DETECTED_VER% is supported^)
echo.

REM --- Step 2: Create Virtual Environment -----------------------
echo [Step 2/5] Creating virtual environment in .venv\ ...
set VENV_OK=0
if exist .venv (
    call :check_venv_version
    if %VENV_OK% equ 1 (
        echo   .venv already exists with correct Python version, skipping.
        goto :venv_done
    ) else (
        echo   .venv exists but has wrong Python version. Recreating...
        rmdir /s /q .venv
    )
)
uv venv --python %PY_VER% .venv
if %errorlevel% neq 0 (
    echo   ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
:venv_done
echo   OK
echo.

REM --- Step 3: Install Dependencies ---------------------------
echo [Step 3/5] Installing dependencies from pyproject.toml (uv sync)...
uv sync
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: uv sync failed. Check the output above for details.
    pause
    exit /b 1
)
echo   OK
echo.

REM --- Step 4: Download language models -----------------------
echo [Step 4/5] Downloading spaCy model and NLTK WordNet corpora...
uv run python scripts\download_models.py
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: Model download failed.
    pause
    exit /b 1
)
echo   OK
echo.

REM --- Done ---------------------------------------------------
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
echo    3. Start FlowState:
echo       uv run python src\main_win.py
echo.
echo    To download/update language models later:
echo       uv run python scripts\download_models.py
echo.
echo  NOTE: Administrator is required because FlowState uses global
echo  keyboard hooks to detect hotkeys like Ctrl+Alt+V. This is a
echo  Windows security requirement, not a FlowState choice.
echo.
pause

REM Clean up temp file on exit
del "%VER_FILE%" >nul 2>&1
exit /b 0

REM ============================================================
REM  Helper: check_python_version
REM  Checks a command (python3, python, py) and sets PYTHON_CMD
REM  if the version is between 3.11 and 3.12 inclusive.
REM ============================================================
:check_python_version
set "TEST_CMD=%~1"
%TEST_CMD% --version >"%VER_FILE%" 2>&1
if %errorlevel% neq 0 exit /b 0

set /p V=<"%VER_FILE%"
for /f "tokens=2 delims= " %%a in ("%V%") do set "V_NUM=%%a"
for /f "tokens=1,2 delims=." %%a in ("%V_NUM%") do (
    set "V_MAJ=%%a"
    set "V_MIN=%%b"
)

if %V_MAJ%==3 if %V_MIN% geq 11 if %V_MIN% leq 12 (
    set "PYTHON_CMD=%TEST_CMD%"
)
exit /b 0

REM ============================================================
REM  Helper: check_venv_version
REM  Checks .venv\Scripts\python.exe version and sets VENV_OK=1
REM  if the minor version matches %PY_MINOR%.
REM ============================================================
:check_venv_version
.venv\Scripts\python.exe --version >"%VER_FILE%" 2>&1
if %errorlevel% neq 0 exit /b 0

set /p V=<"%VER_FILE%"
for /f "tokens=2 delims= " %%a in ("%V%") do set "V_NUM=%%a"
for /f "tokens=1,2 delims=." %%a in ("%V_NUM%") do (
    set "V_MAJ=%%a"
    set "V_MIN=%%b"
)

if %V_MAJ%==3 if %V_MIN%==%PY_MINOR% (
    set "VENV_OK=1"
)
exit /b 0
