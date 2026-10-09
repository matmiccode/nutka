"""Aktualizacje samego programu z GitHub Releases (MATCODE).

Program sprawdza najnowsze wydanie repozytorium (api.github.com/.../releases/latest). Gdy jego wersja jest
wyższa niż WERSJA w app.py, okno pokazuje propozycję z opisem zmian. Po zgodzie pobieramy z wydania
Nutka-Setup.podpis.json (podpis Ed25519 autora: nazwa pliku + wersja + SHA256 instalatora, patrz podpis_wydania.py),
sprawdzamy go kluczem publicznym wkompilowanym poniżej, pobieramy Nutka-Setup.exe, porównujemy SHA256 z podpisaną
i uruchamiamy instalator w trybie /SILENT z /AKTUALIZACJA=1 - instalator zamyka stary program, instaluje nowy
i sam go uruchamia. Wydanie bez prawidłowego podpisu nie jest nawet proponowane: przejęcie konta GitHub nie wystarczy,
żeby podsunąć użytkownikom obcy instalator.

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

from teksty import t

NAZWA_INSTALATORA = "Nutka-Setup.exe"
NAZWA_PODPISU = "Nutka-Setup.podpis.json"  # tworzy podpis_wydania.py (zbuduj.ps1 -Wydanie), leży w wydaniu obok instalatora
FORMAT_PODPISU = 1
# klucz publiczny Ed25519 autora (hex, 32 bajty) - wpisuje go `podpis_wydania.py nowy-klucz`; prywatny leży poza repo
KLUCZ_PUBLICZNY = "89950b1d723828912113ee068f8975dd96aee562f6b1e2d8942f81109895fe67"
USTAWIENIA = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Nutka" / "ustawienia.json"
# testy bez publikowania wydania: ścieżka/URL do JSON-a w formacie api.github.com (patrz CLAUDE.md)
ZMIENNA_TESTU = "NUTKA_TEST_WYDANIE"


def jako_liczby(wersja: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", wersja))


def _test_lokalny(adres: str) -> bool:
    """Plik na dysku zamiast URL-a - tylko w teście z NUTKA_TEST_WYDANIE."""
    return bool(os.environ.get(ZMIENNA_TESTU)) and os.path.exists(adres)


def _pobierz_json(adres: str) -> dict:
    if _test_lokalny(adres):
        return json.loads(Path(adres).read_text(encoding="utf-8"))
    zadanie = urllib.request.Request(adres, headers={"Accept": "application/vnd.github+json",
                                                     "User-Agent": "Nutka-aktualizacje"})
    with urllib.request.urlopen(zadanie, timeout=20) as odp:
        return json.loads(odp.read())


def wiadomosc_podpisu(plik: str, wersja: str, sha256: str) -> bytes:
    """To podpisuje autor i to sprawdza program: podpis wiąże plik z wersją (stare wydanie nie uda nowszego)."""
    return f"nutka-wydanie-{FORMAT_PODPISU}\n{plik}\n{wersja}\n{sha256}".encode()


def sprawdz_podpis(podpis: dict, wersja: str) -> str:
    """Sprawdza Nutka-Setup.podpis.json kluczem publicznym autora; zwraca podpisaną sumę SHA256 instalatora."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if podpis.get("plik") != NAZWA_INSTALATORA or podpis.get("wersja") != wersja:
        raise ValueError(t("Podpis wydania dotyczy innego pliku lub innej wersji - nie instaluję."))
    sha = str(podpis.get("sha256", "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError(t("Podpis wydania nie zawiera poprawnej sumy SHA256 - nie instaluję."))
    try:
        klucz = Ed25519PublicKey.from_public_bytes(bytes.fromhex(KLUCZ_PUBLICZNY))
        klucz.verify(bytes.fromhex(str(podpis.get("podpis", ""))), wiadomosc_podpisu(NAZWA_INSTALATORA, wersja, sha))
    except (InvalidSignature, ValueError):
        raise ValueError(t("Podpis wydania nie zgadza się z kluczem autora - nie instaluję.")) from None
    return sha


def najnowsze_wydanie(repo: str) -> dict | None:
    """{'wersja','opis','url','podpis_url','rozmiar','sha256','strona'} najnowszego wydania z instalatorem;
    None = brak wydania. podpis_url = None, gdy wydanie nie ma pliku podpisu (takiego nie proponujemy)."""
    dane = _pobierz_json(os.environ.get(ZMIENNA_TESTU) or f"https://api.github.com/repos/{repo}/releases/latest")
    pliki = {a.get("name"): a for a in dane.get("assets", [])}
    plik = pliki.get(NAZWA_INSTALATORA)
    if not plik:
        return None

    def adres(asset: dict) -> str:
        # pliki wyłącznie z wydań tego repo przez https (test lokalny: ścieżka na dysku) - inny adres = błąd
        url = asset["browser_download_url"]
        if not (url.startswith(f"https://github.com/{repo}/releases/download/") or _test_lokalny(url)):
            raise ValueError(f"nieoczekiwany adres pliku wydania: {url}")
        return url
    skrot = plik.get("digest") or ""
    return {
        "wersja": dane.get("tag_name", "").lstrip("vV"),
        "opis": dane.get("body") or "",
        "url": adres(plik),
        "podpis_url": adres(pliki[NAZWA_PODPISU]) if NAZWA_PODPISU in pliki else None,
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
    if not wydanie["podpis_url"]:
        raise ValueError(t("Wydanie {wersja} nie ma podpisu autora ({plik}) - nie proponuję aktualizacji.").format(wersja=wydanie["wersja"], plik=NAZWA_PODPISU))
    if not recznie and czytaj_ustawienia().get("pominieta_wersja") == wydanie["wersja"]:
        return None
    return wydanie


def pobierz_instalator(wydanie: dict, postep=lambda procent: None) -> Path:
    """Najpierw podpis autora (mały JSON), potem instalator do %TEMP% kawałkami (postep(0..100)); plik dostaje
    nazwę .exe dopiero, gdy jego SHA256 zgadza się z podpisaną."""
    adres = wydanie["url"]
    oczekiwana = sprawdz_podpis(_pobierz_json(wydanie["podpis_url"]), wydanie["wersja"])
    if wydanie["sha256"] and wydanie["sha256"].lower() != oczekiwana:
        raise ValueError(t("Suma kontrolna z GitHuba różni się od podpisanej przez autora - nie instaluję."))
    gotowy = Path(tempfile.gettempdir()) / f"Nutka-Setup-{wydanie['wersja']}.exe"
    cel = gotowy.with_suffix(".part")  # dopiero po sprawdzeniu sumy -> .exe (urwane/zepsute nigdy nie udaje gotowego)
    skrot = hashlib.sha256()
    if _test_lokalny(adres):
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
    if skrot.hexdigest() != oczekiwana:
        cel.unlink(missing_ok=True)
        raise ValueError(t("Pobrany instalator nie zgadza się z podpisem autora (zła suma kontrolna) - spróbuj ponownie."))
    os.replace(cel, gotowy)
    return gotowy


def uruchom_instalator(plik: Path):
    """Instalator działa dalej sam (osobny proces), program zaraz potem się zamyka."""
    subprocess.Popen([str(plik), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/AKTUALIZACJA=1"],
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0), close_fds=True)
