"""Aktualizacje samego programu z GitHub Releases (MATCODE).

Program sprawdza najnowsze wydanie repozytorium (api.github.com/.../releases/latest). Gdy jego wersja jest
wyższa niż WERSJA w app.py, okno pokazuje propozycję z opisem zmian. Po zgodzie pobieramy Nutka-Setup.exe
z wydania, sprawdzamy sumę SHA256 (GitHub podaje ją przy każdym pliku wydania) i uruchamiamy instalator
w trybie /SILENT z /AKTUALIZACJA=1 - instalator zamyka stary program, instaluje nowy i sam go uruchamia.

Lekkie pakiety (yt-dlp, ytmusicapi, spotapi) aktualizują się osobno i po cichu - aktualizacje.py.
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

NAZWA_INSTALATORA = "Nutka-Setup.exe"
USTAWIENIA = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Nutka" / "ustawienia.json"
# testy bez publikowania wydania: ścieżka/URL do JSON-a w formacie api.github.com (patrz CLAUDE.md)
ZMIENNA_TESTU = "NUTKA_TEST_WYDANIE"


def jako_liczby(wersja: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", wersja))


def _pobierz_json(adres: str) -> dict:
    if os.path.exists(adres):
        return json.loads(Path(adres).read_text(encoding="utf-8"))
    zadanie = urllib.request.Request(adres, headers={"Accept": "application/vnd.github+json",
                                                     "User-Agent": "Nutka-aktualizacje"})
    with urllib.request.urlopen(zadanie, timeout=20) as odp:
        return json.loads(odp.read())


def najnowsze_wydanie(repo: str) -> dict | None:
    """{'wersja','opis','url','rozmiar','sha256','strona'} najnowszego wydania z instalatorem; None = brak/nieosiągalne."""
    dane = _pobierz_json(os.environ.get(ZMIENNA_TESTU) or f"https://api.github.com/repos/{repo}/releases/latest")
    plik = next((a for a in dane.get("assets", []) if a.get("name") == NAZWA_INSTALATORA), None)
    if not plik:
        return None
    skrot = plik.get("digest") or ""
    return {
        "wersja": dane.get("tag_name", "").lstrip("vV"),
        "opis": dane.get("body") or "",
        "url": plik["browser_download_url"],
        "rozmiar": plik.get("size") or 0,
        "sha256": skrot.split(":", 1)[1] if skrot.startswith("sha256:") else None,
        "strona": dane.get("html_url", ""),
    }


def czytaj_ustawienia() -> dict:
    try:
        return json.loads(USTAWIENIA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def zapisz_ustawienie(klucz: str, wartosc):
    ustawienia = czytaj_ustawienia()
    ustawienia[klucz] = wartosc
    try:
        USTAWIENIA.parent.mkdir(parents=True, exist_ok=True)
        USTAWIENIA.write_text(json.dumps(ustawienia, indent=1), encoding="utf-8")
    except OSError:
        pass


def do_zaproponowania(repo: str, obecna: str, recznie: bool = False) -> dict | None:
    """Nowsze wydanie, które warto pokazać (automatycznie pomijamy wersję, którą użytkownik kazał pominąć)."""
    wydanie = najnowsze_wydanie(repo)
    if not wydanie or jako_liczby(wydanie["wersja"]) <= jako_liczby(obecna):
        return None
    if not recznie and czytaj_ustawienia().get("pominieta_wersja") == wydanie["wersja"]:
        return None
    return wydanie


def pobierz_instalator(wydanie: dict, postep=lambda procent: None) -> Path:
    """Pobiera instalator do %TEMP% kawałkami (postep(0..100)) i sprawdza SHA256, jeśli GitHub ją podał."""
    gotowy = Path(tempfile.gettempdir()) / f"Nutka-Setup-{wydanie['wersja']}.exe"
    cel = gotowy.with_suffix(".part")  # dopiero po sprawdzeniu sumy -> .exe (urwane/zepsute nigdy nie udaje gotowego)
    adres = wydanie["url"]
    skrot = hashlib.sha256()
    if os.path.exists(adres):  # test lokalny
        zrodlo, rozmiar = open(adres, "rb"), os.path.getsize(adres)
    else:
        zrodlo = urllib.request.urlopen(urllib.request.Request(adres, headers={"User-Agent": "Nutka-aktualizacje"}),
                                        timeout=60)
        rozmiar = wydanie["rozmiar"] or int(zrodlo.headers.get("Content-Length") or 0)
    pobrane = 0
    with zrodlo, open(cel, "wb") as plik:
        while kawalek := zrodlo.read(1 << 20):
            plik.write(kawalek)
            skrot.update(kawalek)
            pobrane += len(kawalek)
            if rozmiar:
                postep(min(100.0, pobrane * 100 / rozmiar))
    if wydanie["sha256"] and skrot.hexdigest() != wydanie["sha256"]:
        cel.unlink(missing_ok=True)
        raise ValueError("Pobrany instalator jest uszkodzony (zła suma kontrolna) - spróbuj ponownie.")
    os.replace(cel, gotowy)
    return gotowy


def uruchom_instalator(plik: Path):
    """Instalator działa dalej sam (osobny proces), program zaraz potem się zamyka."""
    subprocess.Popen([str(plik), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/AKTUALIZACJA=1"],
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0), close_fds=True)
