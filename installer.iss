; Inno Setup Script for Dead Man's Vault
#define MyAppName "Dead Man's Vault"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Dead Man's Vault Team"
#define MyAppURL "https://github.com/ZimnyySTD/Dead-Man-s-Vault"
#define MyAppExeName "DeadMansVault.exe"

[Setup]
AppId={{5A8E19B2-39C7-4182-9F14-8B8D24E31C01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=DeadMansVault_Setup_v{#MyAppVersion}
SetupIconFile=DeadMansVault\Resources\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\DeadMansVault\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\DeadMansVault\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
