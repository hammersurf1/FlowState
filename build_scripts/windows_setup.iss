; ============================================================
;  FlowState — Windows Installer (Inno Setup)
;  Modern branded installer with informational wizard pages.
; ============================================================

#define MyAppName "FlowState"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "hammersurf1"
#define MyAppURL "https://github.com/hammersurf1/FlowState"
#define MyAppExeName "FlowState.exe"

[Setup]
AppId={{B3F8A2D1-7E4C-4F5A-9D6B-1C2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=FlowState_Windows_Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\LICENSE
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; ── Modern Branding ─────────────────────────────
WizardStyle=modern
WizardImageFile=..\assets\installer\wizard_banner.bmp
WizardSmallImageFile=..\assets\installer\wizard_icon.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startupicon"; Description: "Start FlowState when &Windows starts"; GroupDescription: "Startup:"

[Files]
Source: "..\dist\FlowState\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch FlowState now"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
var
  InfoPage: TOutputMsgWizardPage;
begin
  InfoPage := CreateOutputMsgPage(wpLicense,
    'Important Information',
    'Please read the following before continuing.',
    'FlowState requires the following to work correctly:'#13#10 +
    ''#13#10 +
    Chr(9679) + ' Google Chrome'#13#10 +
    '   FlowState types into Chrome browser tabs using the Chrome'#13#10 +
    '   DevTools Protocol. Please install Chrome if you haven''t already:'#13#10 +
    '   https://www.google.com/chrome'#13#10 +
    ''#13#10 +
    Chr(9679) + ' Administrator Privileges'#13#10 +
    '   Windows requires admin access for apps that register global'#13#10 +
    '   keyboard shortcuts (like Ctrl+Alt+V). FlowState will request'#13#10 +
    '   elevation when it starts.'#13#10 +
    ''#13#10 +
    Chr(9679) + ' Windows SmartScreen'#13#10 +
    '   Since FlowState is not yet signed with a Microsoft certificate,'#13#10 +
    '   Windows may show a SmartScreen warning on first run.'#13#10 +
    '   Click "More info" then "Run anyway" to proceed safely.'#13#10 +
    ''#13#10 +
    'FlowState is free and open-source:'#13#10 +
    'https://github.com/hammersurf1/FlowState');
end;