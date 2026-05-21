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

REM --- Detect uv ------------------------------------------------
set USE_UV=0
uv --version >nul 2>&1
if %errorlevel% equ 0 (
    set USE_UV=1
    echo  [uv detected - using uv for fast install]
    echo.
)

REM --- Step 0: Enforce Python 3.12 ----------------------------
echo [Step 0/5] Ensuring Python %PY_VER% is available...
set PYTHON_CMD=

if %USE_UV% equ 1 goto :uv_find_python
goto :no_uv_find_python

REM --- uv path --------------------------------------------------
:uv_find_python
call :uv_ensure_python
if %errorlevel% neq 0 (
    echo   ERROR: uv failed to provide Python %PY_VER%.
    pause
    exit /b 1
)
goto :python_ok

REM --- non-uv path --------------------------------------------
:no_uv_find_python
call :find_system_python
if not "%PYTHON_CMD%"=="" goto :python_ok

REM No suitable Python found - download and install 3.12 --------
echo.
echo   No suitable Python found. Downloading Python %PY_VER%...
echo   URL: %PY_URL%
echo.

powershell -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%'" >nul 2>&1
if not exist "%PY_INSTALLER%" (
    echo   ERROR: Download failed. Please install Python %PY_VER% manually from
    echo          https://www.python.org/downloads/release/python-31210/
    pause
    exit /b 1
)

echo   Running installer (silent, per-user, adds to PATH)...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Shortcuts=0
if %errorlevel% neq 0 (
    echo   ERROR: Python installer failed (exit %errorlevel%).
    pause
    exit /b 1
)

del "%PY_INSTALLER%" >nul 2>&1

REM Re-check py launcher after install ---------------------------
timeout /t 2 /nobreak >nul 2>&1
py -%PY_VER% --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -%PY_VER%"
    echo   Python %PY_VER% installed and detected via py launcher.
    goto :python_ok
)

echo   ERROR: Python was installed but cannot be found.
pause
exit /b 1

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
if %USE_UV% equ 1 (
    uv venv --python %PY_VER% .venv
) else (
    %PYTHON_CMD% -m venv .venv
)
if %errorlevel% neq 0 (
    echo   ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
:venv_done
echo   OK
echo.

REM --- Step 3: Install Dependencies ---------------------------
echo [Step 3/5] Installing dependencies from requirements_win.txt...
if %USE_UV% equ 1 (
    uv pip install --python .venv\Scripts\python.exe -r requirements_win.txt
) else (
    call .venv\Scripts\activate.bat
    pip install -r requirements_win.txt
)
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: pip install failed. Check the output above for details.
    pause
    exit /b 1
)
echo   OK
echo.

REM --- Step 4: Download spaCy Model ---------------------------
echo [Step 4/5] Downloading spaCy language model (en_core_web_md)...
if %USE_UV% equ 1 (
    uv run --python %PY_VER% python -m spacy download en_core_web_md
) else (
    python -m spacy download en_core_web_md
)
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: spaCy model download failed.
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
if %USE_UV% equ 1 (
echo    3. Start FlowState:
echo       uv run python src\main_win.py
echo.
) else (
echo    3. Activate the virtual environment:
echo       .venv\Scripts\activate
echo.
echo    4. Start FlowState:
echo       python src\main_win.py
echo.
)
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
