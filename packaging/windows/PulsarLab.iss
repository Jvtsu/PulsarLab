; =====================================================
; PulsarLab Installer
; Inno Setup Script
; =====================================================


#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif


#define MyAppName "PulsarLab"
#define MyAppPublisher "Agustín Buruchaga"
#define MyAppExeName "PulsarLab.exe"


[Setup]

AppId={{PULSARLAB-APP-ID}}

AppName={#MyAppName}

AppVersion={#MyAppVersion}

AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\{#MyAppName}

OutputBaseFilename=PulsarLab-Setup-{#MyAppVersion}-Windows-x64

OutputDir=..\..\dist\installer

Compression=lzma

SolidCompression=yes

ArchitecturesInstallIn64BitMode=x64compatible


; Icono del instalador
; Debe existir en la misma carpeta que este archivo .iss
SetupIconFile=pulsarlab.ico



[Languages]

Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"



[Tasks]

Name: "desktopicon"; Description: "Crear acceso directo en escritorio"



[Files]

Source: "..\..\dist\PulsarLab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs



[Icons]

Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon



[Run]

Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar PulsarLab"; Flags: nowait postinstall skipifsilent
