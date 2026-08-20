#ifndef AppVersion
  #define AppVersion "0.6.0"
#endif

[Setup]
AppId={{8D7337D4-8713-4B4C-85D2-56E8E0D3A251}
AppName=Clipora
AppVersion={#AppVersion}
AppVerName=Clipora {#AppVersion}
AppPublisher=ertyu.dev
AppPublisherURL=https://ertyu.dev
AppSupportURL=https://github.com/ertyu007/media-toolkit-Open-source/issues
AppUpdatesURL=https://github.com/ertyu007/media-toolkit-Open-source/releases
AppCopyright=Copyright (C) ertyu.dev
AppComments=Download, convert and extract audio from authorized media on your PC
DefaultDirName={autopf}\Clipora
DefaultGroupName=Clipora
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=Clipora-Setup-{#AppVersion}-x64
SetupIconFile=..\assets\clipora.ico
UninstallDisplayName=Clipora
UninstallDisplayIcon={app}\Clipora.exe
VersionInfoDescription=Clipora desktop media toolkit
VersionInfoCopyright=GNU GPL v3
VersionInfoProductName=Clipora
VersionInfoProductVersion={#AppVersion}
VersionInfoOriginalFileName=Clipora-Setup-{#AppVersion}-x64.exe
LicenseFile=..\LICENSE
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
SetupLogging=yes
AppMutex=Clipora-8D7337D4-8713-4B4C-85D2-56E8E0D3A251
MinVersion=10.0.17763

[Files]
Source: "..\dist\Clipora\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Clipora"; Filename: "{app}\Clipora.exe"
Name: "{autodesktop}\Clipora"; Filename: "{app}\Clipora.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "สร้างไอคอนบน Desktop"; GroupDescription: "ไอคอนเพิ่มเติม:"; Flags: unchecked

[Run]
Filename: "{app}\Clipora.exe"; Description: "เปิด Clipora"; Flags: nowait postinstall skipifsilent runascurrentuser
