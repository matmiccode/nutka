# Nutka - budowanie instalatora i wydania (MATCODE)
#
# Wynik: dist\Nutka-Setup.exe - jeden plik z wszystkim w środku (Python, yt-dlp, ytmusicapi, spotapi,
# ffmpeg/ffprobe/ffplay, deno). Instaluje się bez admina; potem sam po cichu aktualizuje lekkie pakiety
# (aktualizacje.py), a o nowej wersji całego programu dowiaduje się z GitHub Releases (aktualizacja_programu.py).
#
# Wymaga: Python 3.12 (py -3.12), Inno Setup 6, internet; do -Wydanie także gh (zalogowany) i Dysk Google.
#
#   zbuduj.ps1                 sam build do dist\ (nic nie publikuje - do testów)
#   zbuduj.ps1 -Wydanie        build + wydanie vX.Y.Z na GitHubie (instalator + instrukcja PDF, opis z CHANGELOG.md)
#                              + kopia na Dysk Google (folder użytkowników z publikacja.local.json)
#   zbuduj.ps1 -TylkoPublikacja  tylko kopia dist\ na Dysk Google (np. po nowym PDF instrukcji)
#   zbuduj.ps1 -Pakiety "yt-dlp==2026.7.4,ytmusicapi==1.11.5"  celowo stare pakiety = test cichych aktualizacji
#
# Wersję bierzemy z WERSJA w app.py (jedno źródło prawdy) - przed wydaniem podbij ją i dopisz sekcję w CHANGELOG.md.

param([string]$Pakiety = "", [switch]$Wydanie, [switch]$TylkoPublikacja)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-Location $PSScriptRoot

$Wersja = [regex]::Match((Get-Content app.py -Raw -Encoding UTF8), 'WERSJA = "([\d.]+)"').Groups[1].Value
if (-not $Wersja) { throw "Nie znalazłem WERSJA = ""x.y.z"" w app.py" }

function Krok([string]$opis) { Write-Host "`n=== $opis" -ForegroundColor Cyan }
function Sprawdz([string]$co) { if ($LASTEXITCODE -ne 0) { throw "$co nie wyszło (kod $LASTEXITCODE)" } }

# folder użytkowników na Dysku Google - jego ID jest tylko lokalnie w publikacja.local.json (poza gitem:
# repo jest publiczne), szukany po ID, bo nazwa i litera dysku mogą się zmienić
function Opublikuj-NaDysku {
    $konfig = Join-Path $PSScriptRoot "publikacja.local.json"
    if (-not (Test-Path $konfig)) { Write-Host "Brak publikacja.local.json - pomijam Dysk Google."; return }
    $DyskGoogleId = (Get-Content $konfig -Raw | ConvertFrom-Json).dysk_google_id
    $folder = Get-PSDrive -PSProvider FileSystem | ForEach-Object {
        Get-ChildItem (Join-Path $_.Root ".shortcut-targets-by-id\$DyskGoogleId") -Directory -ErrorAction SilentlyContinue
    } | Select-Object -First 1
    if (-not $folder) {
        Write-Host "Nie widzę folderu na Dysku Google - uruchom Dysk Google na komputerze i odpal: zbuduj.ps1 -TylkoPublikacja" -ForegroundColor Yellow
        return
    }
    foreach ($plik in "Nutka-Setup.exe", "Nutka-instrukcja.pdf") {
        $zrodlo = Join-Path $PSScriptRoot "dist\$plik"
        if (-not (Test-Path $zrodlo)) { Write-Host "  brak dist\$plik - pomijam"; continue }
        $cel = Join-Path $folder.FullName $plik
        if ((Test-Path $cel) -and (Get-FileHash $cel).Hash -eq (Get-FileHash $zrodlo).Hash) {
            Write-Host "  $plik - bez zmian"
        } else {
            Copy-Item $zrodlo $cel -Force
            Write-Host "  $plik -> Dysk Google (wyśle go w tle)" -ForegroundColor Green
        }
    }
}

function Wydaj-NaGitHubie {
    if (git status --porcelain) { throw "Są niezacommitowane zmiany - najpierw commit i push, potem wydanie." }
    git push -q; Sprawdz "git push"
    $changelog = Get-Content CHANGELOG.md -Raw -Encoding UTF8
    $sekcja = [regex]::Match($changelog, "(?ms)^## \[$([regex]::Escape($Wersja))\][^\n]*\n(.*?)(?=^## \[|\z)").Groups[1].Value.Trim()
    if (-not $sekcja) { throw "Brak sekcji ## [$Wersja] w CHANGELOG.md - to jest opis 'Co nowego' w programie." }
    $notatki = Join-Path $env:TEMP "nutka-notatki.md"
    [IO.File]::WriteAllText($notatki, $sekcja, [Text.UTF8Encoding]::new($false))
    $pliki = @("dist\Nutka-Setup.exe") + @(Get-Item "dist\Nutka-instrukcja.pdf" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    gh release create "v$Wersja" @pliki --title "Nutka $Wersja" --notes-file $notatki; Sprawdz "gh release create"
    Write-Host "Wydanie v$Wersja jest na GitHubie - zainstalowane programy zaproponują aktualizację." -ForegroundColor Green
}

if ($TylkoPublikacja) {
    Opublikuj-NaDysku
    exit 0
}

$build = Join-Path $PSScriptRoot "build"
$venv = Join-Path $build "venv"
$py = Join-Path $venv "Scripts\python.exe"
$narzedzia = Join-Path $build "narzedzia"
$FfmpegZip = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"

Write-Host "Nutka $Wersja" -ForegroundColor Cyan
if ($Wydanie -and $Pakiety) { throw "-Wydanie z -Pakiety (celowo starymi) nie ma sensu - to build testowy." }

Krok "Środowisko do budowania (świeże pakiety)"
if (-not (Test-Path $py)) {
    py -3.12 -m venv $venv; Sprawdz "Tworzenie venv"
}
& $py -m pip install -q --disable-pip-version-check -U -r requirements.txt pyinstaller; Sprawdz "pip install"
# yt-dlp w wersji nightly - tak jak ciche aktualizacje (patrz NIGHTLY w aktualizacje.py)
& $py -m pip install -q --disable-pip-version-check -U --pre "yt-dlp[default]"; Sprawdz "pip install yt-dlp nightly"
if ($Pakiety) {
    & $py -m pip install -q --disable-pip-version-check @($Pakiety -split "[, ]+" | Where-Object { $_ }); Sprawdz "pip install $Pakiety"
}

Krok "ffmpeg + ffprobe + ffplay (build shared - wspólne DLL, mniejszy rozmiar)"
if (Test-Path $narzedzia) { Remove-Item $narzedzia -Recurse -Force }
New-Item -ItemType Directory -Force $narzedzia | Out-Null
$zip = Join-Path $build "ffmpeg.zip"
if (-not (Test-Path $zip) -or ((Get-Item $zip).LastWriteTime -lt (Get-Date).AddDays(-7))) {
    Invoke-WebRequest $FfmpegZip -OutFile $zip -UseBasicParsing
}
tar -xf $zip -C $build; Sprawdz "Rozpakowanie ffmpeg"
$rozpakowany = Get-ChildItem $build -Directory -Filter "ffmpeg-*-win64-gpl-shared" | Select-Object -First 1
Copy-Item "$($rozpakowany.FullName)\bin\*" $narzedzia
Copy-Item "$($rozpakowany.FullName)\LICENSE.txt" "$narzedzia\LICENSE-ffmpeg.txt"
Remove-Item $rozpakowany.FullName -Recurse -Force

Krok "deno (z paczki pip)"
Copy-Item (Join-Path $venv "Scripts\deno.exe") $narzedzia

Krok "Informacje o pliku exe (wydawca, wersja)"
$w = $Wersja.Split("."); while ($w.Count -lt 4) { $w += "0" }
$krotka = ($w -join ", ")
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($krotka), prodvers=($krotka)),
  kids=[
    StringFileInfo([StringTable('041504B0', [
      StringStruct('CompanyName', 'MATCODE'),
      StringStruct('FileDescription', 'Nutka - pobieranie mp3 z YouTube i Spotify'),
      StringStruct('FileVersion', '$Wersja'),
      StringStruct('InternalName', 'Nutka'),
      StringStruct('LegalCopyright', '(c) $(Get-Date -Format yyyy) MATCODE'),
      StringStruct('OriginalFilename', 'Nutka.exe'),
      StringStruct('ProductName', 'Nutka'),
      StringStruct('ProductVersion', '$Wersja')])]),
    VarFileInfo([VarStruct('Translation', [0x0415, 1200])])
  ]
)
"@ | Set-Content (Join-Path $build "wersja.txt") -Encoding UTF8

Krok "PyInstaller (katalog, nie onefile - szybszy start i mniej fałszywych alarmów antywirusów)"
& $py -m PyInstaller --noconfirm --clean --windowed --noupx `
    --name Nutka `
    --icon (Join-Path $PSScriptRoot "ikona.ico") `
    --splash (Join-Path $PSScriptRoot "splash.png") `
    --add-data "$PSScriptRoot\ikona.ico;." `
    --add-data "$PSScriptRoot\naglowek.png;." `
    --version-file (Join-Path $build "wersja.txt") `
    --collect-all ytmusicapi `
    --collect-all yt_dlp_ejs `
    --collect-all spotapi `
    --collect-all customtkinter `
    --collect-submodules yt_dlp `
    --copy-metadata yt-dlp `
    --copy-metadata yt-dlp-ejs `
    --copy-metadata ytmusicapi `
    --copy-metadata spotapi `
    --exclude-module spotdl `
    --distpath (Join-Path $build "dist") `
    --workpath (Join-Path $build "pyinstaller") `
    --specpath $build `
    (Join-Path $PSScriptRoot "app.py")
Sprawdz "PyInstaller"
Copy-Item $narzedzia (Join-Path $build "dist\Nutka\narzedzia") -Recurse
Copy-Item LICENSE, THIRD-PARTY.md (Join-Path $build "dist\Nutka") -ErrorAction SilentlyContinue
# instrukcja obok Nutka.exe - otwiera ją przycisk Instrukcja w nagłówku (działa bez internetu)
if (Test-Path "dist\Nutka-instrukcja.pdf") {
    Copy-Item "dist\Nutka-instrukcja.pdf" (Join-Path $build "dist\Nutka")
} elseif ($Wydanie) {
    throw "Brak dist\Nutka-instrukcja.pdf - przycisk Instrukcja w programie nie miałby czego otworzyć."
} else {
    Write-Host "Brak dist\Nutka-instrukcja.pdf - build bez instrukcji (przycisk pokaże komunikat)." -ForegroundColor Yellow
}

Krok "Instalator (Inno Setup)"
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Brak Inno Setup 6 (winget install JRSoftware.InnoSetup)" }
& $iscc /Q "/DWersja=$Wersja" instalator.iss; Sprawdz "Inno Setup"

$wynik = Get-Item (Join-Path $PSScriptRoot "dist\Nutka-Setup.exe")
Write-Host "`nGotowe: $($wynik.FullName) ($([int]($wynik.Length / 1MB)) MB), wersja $Wersja" -ForegroundColor Green

if ($Wydanie) {
    Krok "Wydanie na GitHubie"
    Wydaj-NaGitHubie
    Krok "Kopia na Dysk Google (folder użytkowników)"
    Opublikuj-NaDysku
}
