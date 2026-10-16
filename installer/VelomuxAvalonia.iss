; Velomux Avalonia Windows x64 installer (private release-candidate package)
#define ProductName "Velomux"
#define ProductVersion "0.4.0"
#define MainExecutable "Velomux.exe"

[Setup]
AppId=Velomux.Avalonia.MediaWorkstation
AppName={#ProductName} Avalonia
AppVersion={#ProductVersion}
AppVerName={#ProductName} {#ProductVersion} (Avalonia)
AppPublisher=Adam Knight
AppPublisherURL=https://github.com/admknight/Velomux
AppSupportURL=https://github.com/admknight/Velomux/issues
DefaultDirName={localappdata}\Programs\Velomux-Avalonia
DefaultGroupName=Velomux
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
SetupIconFile=..\assets\velomux.ico
UninstallDisplayIcon={app}\{#MainExecutable}
OutputDir=..\avalonia-spike\installer-output
OutputBaseFilename=Velomux-Avalonia-Setup-{#ProductVersion}-Win-x64
Compression=lzma2
SolidCompression=yes
CloseApplications=no
RestartApplications=no
VersionInfoVersion=0.4.0.0
VersionInfoDescription=Velomux Avalonia media workstation
VersionInfoProductName={#ProductName}
VersionInfoProductVersion={#ProductVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "explorercontext"; Description: "Add Open in Velomux (Avalonia) to Windows Explorer"; GroupDescription: "Optional Explorer integration:"; Flags: unchecked

[Files]
Source: "..\avalonia-spike\publish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Velomux Avalonia"; Filename: "{app}\{#MainExecutable}"
Name: "{autodesktop}\Velomux Avalonia"; Filename: "{app}\{#MainExecutable}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\*\shell\VelomuxAvalonia"; ValueType: string; ValueData: "Open in Velomux (Avalonia)"; Tasks: explorercontext; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\VelomuxAvalonia"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MainExecutable}"; Tasks: explorercontext
Root: HKCU; Subkey: "Software\Classes\*\shell\VelomuxAvalonia\command"; ValueType: string; ValueData: """{app}\{#MainExecutable}"" ""%1"""; Tasks: explorercontext

[Run]
Filename: "{app}\{#MainExecutable}"; Description: "Launch Velomux"; Flags: nowait postinstall skipifsilent
