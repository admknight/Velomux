; Velomux Windows x64 installer - Inno Setup 7
; Local preview builds only until third-party licensing and runtime gates pass.
#define ProductName "Velomux"
#define ProductVersion "0.2.3"
#define ProductEdition "Preview"
#define MainExecutable "Velomux.exe"

[Setup]
AppId=Velomux.MediaConverter
AppName={#ProductName}
AppVersion={#ProductVersion}
AppVerName={#ProductName} {#ProductVersion} {#ProductEdition}
AppPublisher=Velomux Contributors
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
VersionInfoVersion=0.2.3.0
VersionInfoDescription=Velomux media converter preview installer
VersionInfoProductName={#ProductName}
VersionInfoProductVersion={#ProductVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\Velomux\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Velomux"; Filename: "{app}\{#MainExecutable}"; IconFilename: "{app}\{#MainExecutable}"
Name: "{autodesktop}\Velomux"; Filename: "{app}\{#MainExecutable}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MainExecutable}"; Description: "Launch Velomux"; Flags: nowait postinstall skipifsilent
