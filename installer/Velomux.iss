; Velomux Windows x64 installer - Inno Setup 7
; Local preview builds only until third-party licensing and runtime gates pass.
#define ProductName "Velomux"
#define ProductVersion "0.3.1"
#define ProductEdition "Preview"
#define MainExecutable "Velomux.exe"

[Setup]
AppId=Velomux.MediaConverter
AppName={#ProductName}
AppVersion={#ProductVersion}
AppVerName={#ProductName} {#ProductVersion} {#ProductEdition}
AppPublisher=Adam Knight
AppPublisherURL=https://github.com/admknight/Velomux
AppSupportURL=https://github.com/admknight/Velomux/issues
AppUpdatesURL=https://github.com/admknight/Velomux/releases
DefaultDirName={localappdata}\Programs\{#ProductName}
DefaultGroupName={#ProductName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
SetupIconFile=..\assets\velomux.ico
UninstallDisplayIcon={app}\{#MainExecutable}
OutputDir=..\dist\installer
OutputBaseFilename=Velomux-Setup-{#ProductVersion}-preview-Win-x64
Compression=lzma2
SolidCompression=yes
CloseApplications=no
RestartApplications=no
VersionInfoVersion=0.3.1.0
VersionInfoDescription=Velomux media converter - Adam Knight, Creator & Lead Maintainer
VersionInfoProductName={#ProductName}
VersionInfoProductVersion={#ProductVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "explorercontext"; Description: "Add Open in Velomux to Windows Explorer file menus"; GroupDescription: "Optional Windows integration:"; Flags: unchecked

[Files]
Source: "..\dist\Velomux\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Velomux"; Filename: "{app}\{#MainExecutable}"; IconFilename: "{app}\{#MainExecutable}"
Name: "{autodesktop}\Velomux"; Filename: "{app}\{#MainExecutable}"; Tasks: desktopicon

[Registry]
; Explicit opt-in, per-user only. Windows 11 may show this in Show more options.
; Uninstallation removes our own verb. We do not hijack file associations.
Root: HKCU; Subkey: "Software\Classes\*\shell\Velomux"; ValueType: string; ValueData: "Open in Velomux"; Tasks: explorercontext; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\Velomux"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MainExecutable}"; Tasks: explorercontext
Root: HKCU; Subkey: "Software\Classes\*\shell\Velomux\command"; ValueType: string; ValueData: """{app}\{#MainExecutable}"" ""%1"""; Tasks: explorercontext

[Run]
Filename: "{app}\{#MainExecutable}"; Description: "Launch Velomux"; Flags: nowait postinstall skipifsilent
