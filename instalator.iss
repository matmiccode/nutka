; Nutka - instalator (MATCODE)
; Budowany przez zbuduj.ps1 z katalogu build\dist\Nutka.
; Instalacja per-użytkownik: bez uprawnień administratora, do %LOCALAPPDATA%\Programs.

#ifndef Wersja
  #define Wersja "1.0.0"
#endif

[Setup]
AppId={{FFAFE4E5-9ADE-42CE-9A0A-72191F855F80}
AppName=Nutka
AppVersion={#Wersja}
AppVerName=Nutka {#Wersja}
AppPublisher=MATCODE
AppCopyright=(c) MATCODE
VersionInfoCompany=MATCODE
VersionInfoDescription=Nutka - instalator
VersionInfoVersion={#Wersja}
DefaultDirName={autopf}\Nutka
DefaultGroupName=Nutka
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=Nutka-Setup
SetupIconFile=ikona.ico
UninstallDisplayIcon={app}\Nutka.exe
UninstallDisplayName=Nutka
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
; język instalatora z Windows (polski albo angielski); pytanie tylko, gdy Windows mówi innym językiem
ShowLanguageDialog=auto

[Languages]
Name: "polski"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
polski.SkrotPulpit=Skrót na pulpicie
english.SkrotPulpit=Desktop shortcut
polski.Skroty=Skróty:
english.Skroty=Shortcuts:
polski.Odinstaluj=Odinstaluj Nutkę
english.Odinstaluj=Uninstall Nutka
polski.Uruchom=Uruchom Nutkę
english.Uruchom=Launch Nutka

[Tasks]
Name: "pulpit"; Description: "{cm:SkrotPulpit}"; GroupDescription: "{cm:Skroty}"

[Files]
Source: "build\dist\Nutka\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; przy aktualizacji usuń stare biblioteki, żeby nie mieszały się wersje
Type: filesandordirs; Name: "{app}\_internal"
; i po cichu pobrane pakiety (aktualizacje.py) - nowy exe ma w sobie świeższe, stare by je przykryły
Type: filesandordirs; Name: "{localappdata}\Nutka\pakiety"

[UninstallDelete]
; ciche aktualizacje yt-dlp/ytmusicapi (aktualizacje.py)
Type: filesandordirs; Name: "{localappdata}\Nutka"

[Icons]
Name: "{group}\Nutka"; Filename: "{app}\Nutka.exe"
Name: "{group}\{cm:Odinstaluj}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Nutka"; Filename: "{app}\Nutka.exe"; Tasks: pulpit

[Run]
Filename: "{app}\Nutka.exe"; Description: "{cm:Uruchom}"; Flags: nowait postinstall skipifsilent
; aktualizacja z programu (/SILENT /AKTUALIZACJA=1): bez pytań uruchom nową wersję
Filename: "{app}\Nutka.exe"; Flags: nowait; Check: CzyAktualizacja

[Code]
function CzyAktualizacja: Boolean;
begin
  Result := ExpandConstant('{param:AKTUALIZACJA|0}') = '1';
end;
