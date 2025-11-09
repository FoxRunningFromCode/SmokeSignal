; Inno Setup script template for SmokeSignal
; Update AppVersion, DefaultDirName, OutputDir, and other fields as needed.
[Setup]
AppName=SmokeSignal
AppVersion=1.0
DefaultDirName={pf}\SmokeSignal
DefaultGroupName=SmokeSignal
OutputDir=installer_output
OutputBaseFilename=SmokeSignal_Setup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Include the built distribution folder (one-folder build) - adjust paths if you used --onefile
Source: "dist\\SmokeSignal\\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SmokeSignal"; Filename: "{app}\\SmokeSignal.exe"

[Run]
Filename: "{app}\\SmokeSignal.exe"; Description: "Launch SmokeSignal"; Flags: nowait postinstall skipifsilent
