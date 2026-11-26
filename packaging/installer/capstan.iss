; Capstan installer for GitHub Releases (Inno Setup 6). Built by packaging\build.ps1:
;   ISCC /DAppVersion=1.5.0 /DSourceDir=<dist\Capstan> /DOutDir=<out> capstan.iss
; Per-user install, no admin prompt. Uninstalling keeps the user's data
; (%APPDATA%\Capstan) and every downloaded model.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\Capstan"
#endif
#ifndef OutDir
  #define OutDir "..\out"
#endif

[Setup]
; Never change AppId: Windows uses it to recognise upgrades.
AppId={{87397A84-AFD9-4DA7-887A-45FEE9FC1E47}
AppName=Capstan
AppVersion={#AppVersion}
AppVerName=Capstan {#AppVersion}
AppPublisher=VULLKI
AppPublisherURL=https://vullki.com
AppSupportURL=https://github.com/Vullki/capstan/issues
AppUpdatesURL=https://github.com/Vullki/capstan/releases
AppCopyright=Copyright (c) 2026 VULLKI
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\Capstan
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir={#OutDir}
OutputBaseFilename=Capstan-{#AppVersion}-Setup
SetupIconFile=..\..\app\ui\assets\capstan.ico
UninstallDisplayIcon={app}\Capstan.exe
UninstallDisplayName=Capstan
LicenseFile=..\..\LICENSE
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; An upgrade replaces the whole bundle, so no file from an older version lingers.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
; The AppUserModelID matches APP_ID in app\main.py, so the window groups under this shortcut.
Name: "{autoprograms}\Capstan"; Filename: "{app}\Capstan.exe"; AppUserModelID: "VULLKI.Capstan"; Comment: "Find Hugging Face models that fit your GPU"
Name: "{autodesktop}\Capstan"; Filename: "{app}\Capstan.exe"; AppUserModelID: "VULLKI.Capstan"; Tasks: desktopicon

[Run]
Filename: "{app}\Capstan.exe"; Description: "{cm:LaunchProgram,Capstan}"; Flags: nowait postinstall skipifsilent
