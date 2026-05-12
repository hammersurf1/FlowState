[Setup]
AppName=FlowState
AppVersion=1.0
AppPublisher=hammersurf1
AppPublisherURL=https://github.com/hammersurf1/FlowState
AppSupportURL=https://github.com/hammersurf1/FlowState/issues
DefaultDirName={autopf}\FlowState
DefaultGroupName=FlowState
OutputDir=dist
OutputBaseFilename=FlowState_Windows_Setup
LicenseFile=LICENSE
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "dist\FlowState.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FlowState"; Filename: "{app}\FlowState.exe"; IconFilename: "{app}\FlowState.exe"
Name: "{autodesktop}\FlowState"; Filename: "{app}\FlowState.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"