[Setup]
AppName=AutoTyper
AppVersion=1.0
DefaultDirName={autopf}\AutoTyper
DefaultGroupName=AutoTyper
OutputDir=..\dist
OutputBaseFilename=AutoTyper_Windows_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
; This grabs the PyInstaller output and packages it
Source: "..\dist\AutoTyper.exe"; DestDir: "{app}"; Flags: ignoreversion[Icons]
; Creates Start Menu and Desktop shortcuts
Name: "{group}\AutoTyper"; Filename: "{app}\AutoTyper.exe"; IconFilename: "{app}\AutoTyper.exe"
Name: "{autodesktop}\AutoTyper"; Filename: "{app}\AutoTyper.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"