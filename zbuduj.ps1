# Nutka - budowanie instalatora i wydania (MATCODE)
#
# Wynik: dist\Nutka-Setup.exe - jeden plik z wszystkim w środku (Python, yt-dlp, ytmusicapi, spotapi,
# ffmpeg/ffprobe/ffplay, deno). Instaluje się bez admina; potem sam po cichu aktualizuje lekkie pakiety
# (aktualizacje.py), a o nowej wersji całego programu dowiaduje się z GitHub Releases (aktualizacja_programu.py).
#
# Wymaga: Python 3.12 (py -3.12), Inno Setup 6, internet; do -Wydanie także gh (zalogowany).
#
#   zbuduj.ps1                 sam build do dist\ (nic nie publikuje - do testów)
#   zbuduj.ps1 -Wydanie        build + wydanie vX.Y.Z na GitHubie (instalator + podpis Ed25519, opis z CHANGELOG.md);
#                              wymaga klucza prywatnego z podpis_wydania.py (poza repo, %APPDATA%\MATCODE)
#   zbuduj.ps1 -Pakiety "yt-dlp==2026.7.4,ytmusicapi==1.11.5"  celowo stare pakiety = test cichych aktualizacji
#
# Wersję bierzemy z WERSJA w app.py (jedno źródło prawdy) - przed wydaniem podbij ją i dopisz sekcję w CHANGELOG.md.

param([string]$Pakiety = "", [switch]$Wydanie)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-Location $PSScriptRoot

$Wersja = [regex]::Match((Get-Content app.py -Raw -Encoding UTF8), 'WERSJA = "([\d.]+)"').Groups[1].Value
if (-not $Wersja) { throw "Nie znalazłem WERSJA = ""x.y.z"" w app.py" }

function Krok([string]$opis) { Write-Host "`n=== $opis" -ForegroundColor Cyan }
function Sprawdz([string]$co) { if ($LASTEXITCODE -ne 0) { throw "$co nie wyszło (kod $LASTEXITCODE)" } }

function Wydaj-NaGitHubie {
    if (git status --porcelain) { throw "Są niezacommitowane zmiany - najpierw commit i push, potem wydanie." }
    if (-not (& $py -c "import aktualizacja_programu as a; print(a.KLUCZ_PUBLICZNY)")) { throw "Brak KLUCZ_PUBLICZNY w aktualizacja_programu.py - odpal podpis_wydania.py nowy-klucz." }
    git push -q; Sprawdz "git push"
    $changelog = Get-Content CHANGELOG.md -Raw -Encoding UTF8
    $sekcja = [regex]::Match($changelog, "(?ms)^## \[$([regex]::Escape($Wersja))\][^\n]*\n(.*?)(?=^## \[|\z)").Groups[1].Value.Trim()
    if (-not $sekcja) { throw "Brak sekcji ## [$Wersja] w CHANGELOG.md - to jest opis 'Co nowego' w programie." }
    $notatki = Join-Path $env:TEMP "nutka-notatki.md"
    [IO.File]::WriteAllText($notatki, $sekcja, [Text.UTF8Encoding]::new($false))
    # podpis autora: bez pliku Nutka-Setup.podpis.json zainstalowane Nutki nie zaproponują tej wersji
    & $py podpis_wydania.py podpisz "dist\Nutka-Setup.exe" $Wersja; Sprawdz "podpis wydania"
    gh release create "v$Wersja" "dist\Nutka-Setup.exe" "dist\Nutka-Setup.podpis.json" --title "Nutka $Wersja" --notes-file $notatki; Sprawdz "gh release create"
    Write-Host "Wydanie v$Wersja jest na GitHubie - zainstalowane programy zaproponują aktualizację." -ForegroundColor Green
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
# instrukcja obok Nutka.exe (podfolder instrukcja\) - otwiera ją przycisk Instrukcja w nagłówku, działa bez internetu;
# to ta sama strona, co docs/instrukcja.html na GitHub Pages
$instrukcja = Join-Path $build "dist\Nutka\instrukcja"
New-Item -ItemType Directory -Force $instrukcja | Out-Null
Copy-Item "docs\instrukcja.html", "docs\zrzut-wyszukiwarka.png", "docs\zrzut-playlista.png", "docs\ikona.png", "docs\favicon.png" $instrukcja

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
}
