@echo off
echo Building AutoTyper for Windows...

cd ..

:: 1. Compile Python to a standalone .exe
:: We MUST use --collect-all playwright so PyInstaller grabs the background drivers!
uv run pyinstaller --noconsole --onefile --icon="assets\icon.ico" --name="AutoTyper" --collect-all playwright src\main_win.py

:: 2. Package into an Installer using Inno Setup
echo Creating Windows Installer...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build_scripts\windows_setup.iss

echo Done! Check the "dist" folder for AutoTyper_Windows_Setup.exe.
pause