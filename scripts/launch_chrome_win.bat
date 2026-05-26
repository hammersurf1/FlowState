@echo off
setlocal enabledelayedexpansion

:: FlowState Chrome Launcher for Windows
:: Opens Chrome with a dedicated profile and remote debugging port 9225.
:: FlowState auto-detects this browser and uses Playwright/CDP mode.
::
:: Usage: Double-click this shortcut or run from Start Menu.

setlocal
set "PROFILE_DIR=%LOCALAPPDATA%\FlowState\ChromeProfile"

:: Create profile directory if needed
if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

:: Find Chrome
set "CHROME="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if "%CHROME%"=="" (
    echo Chrome not found. Please install Google Chrome.
    pause
    exit /b 1
)

echo Launching FlowState Chrome with debugging port 9225...
echo.
echo This browser has its own profile with the marker "FlowStateChromeProfile."
echo FlowState detects it and types via Playwright when this window has focus.
echo Press Ctrl+Alt+V in this Chrome to use Playwright mode.
echo Press Ctrl+Alt+V anywhere else to use OS-level mode.
echo.
echo DO NOT close this window while using FlowState Chrome.

start "" "%CHROME%" ^
    --remote-debugging-port=9225 ^
    --user-data-dir="%PROFILE_DIR%" ^
    --no-first-run ^
    --no-default-browser-check

:: Wait a moment for Chrome to start, then launch FlowState if not already running
timeout /t 2 /nobreak >nul

:: Optionally start FlowState tray app
set "FLOWSTATE_EXE=%PROGRAMFILES%\FlowState\FlowState.exe"
if exist "%FLOWSTATE_EXE%" (
    start "" "%FLOWSTATE_EXE%"
)
