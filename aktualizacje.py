"""Ciche aktualizacje lekkich pakietów w wersji exe (MATCODE).

YouTube co jakiś czas coś zmienia i stary yt-dlp przestaje pobierać, a stare ytmusicapi - szukać;
Spotify podobnie psuje spotapi.
Oba to czysty Python, więc zamiast przebudowywać instalator:
  1. w tle sprawdzamy na PyPI, czy jest nowsza wersja,
  2. pobieramy wheel (zip) i rozpakowujemy do %LOCALAPPDATA%\\Nutka\\pakiety\\<pakiet>-<wersja>,
  3. sprawdzamy w osobnym procesie, czy się importuje - dopiero wtedy zapisujemy go jako aktywny,
  4. przy każdym starcie procesu zastosuj() wstawia aktywne katalogi na początek sys.path,
     więc przykrywają wersje wbudowane w exe (PyInstaller 6 szuka modułów po kolejności sys.path).
Ciężkie rzeczy (Python, ffmpeg, deno) zostają w instalatorze.
"""

import compileall
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from importlib import metadata
from pathlib import Path

FOLDER = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Nutka" / "pakiety"
STAN = FOLDER / "aktywne.json"
# yt-dlp-ejs (skrypty do łamania zabezpieczeń YouTube) aktualizujemy w wersji, której wymaga nowy yt-dlp
PAKIETY = ("yt-dlp", "ytmusicapi", "spotapi")  # spotapi = odczyt list ze Spotify (spotify_lista.py)
# yt-dlp sam zaleca wersje nightly (na PyPI jako .devN) - poprawki pod zmiany YouTube trafiają tam od razu,
# do wydania stabilnego często dopiero po tygodniach
NIGHTLY = {"yt-dlp"}
ZMIENNA_TESTU = "MUZYKA_PAKIETY_TEST"  # kandydat do sprawdzenia w procesie potomnym, zanim trafi do STAN
BEZ_OKNA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def zapisz_log(tekst: str):
    """aktualizacje.log obok pakietów - jedyny ślad cichych aktualizacji (pokazuje go też --autotest)."""
    from datetime import datetime
    try:
        FOLDER.mkdir(parents=True, exist_ok=True)
        log = FOLDER / "aktualizacje.log"
        if log.exists() and log.stat().st_size > 100_000:
            log.unlink()
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M} {tekst}\n")
    except OSError:
        pass


def _wczytaj_stan() -> dict[str, str]:
    try:
        return json.loads(STAN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def zastosuj():
    """Wywoływane na starcie każdego procesu exe: zaktualizowane pakiety przed wbudowanymi."""
    stan = json.loads(os.environ[ZMIENNA_TESTU]) if ZMIENNA_TESTU in os.environ else _wczytaj_stan()
    for katalog in stan.values():
        if Path(katalog).is_dir() and katalog not in sys.path:
            sys.path.insert(0, katalog)


def wersja(pakiet: str) -> str:
    try:
        return metadata.version(pakiet)
    except metadata.PackageNotFoundError:
        return "0"


def _jako_liczby(w: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", w))


def _pobierz(url: str) -> bytes:
    zadanie = urllib.request.Request(url, headers={"User-Agent": "Nutka"})
    with urllib.request.urlopen(zadanie, timeout=30) as odp:
        return odp.read()


def _najnowsza(pakiet: str) -> str:
    info = json.loads(_pobierz(f"https://pypi.org/pypi/{pakiet}/json"))
    if pakiet not in NIGHTLY:
        return info["info"]["version"]
    z_wheelem = [w for w, pliki in info["releases"].items()
                 if any(p["packagetype"] == "bdist_wheel" and not p.get("yanked") for p in pliki)]
    return max(z_wheelem, key=_jako_liczby)


def _rozpakuj_wheel(pakiet: str, wer: str) -> Path:
    """Pobiera wheel z PyPI (sprawdza sumę SHA256) i rozpakowuje do własnego katalogu."""
    info = json.loads(_pobierz(f"https://pypi.org/pypi/{pakiet}/{wer}/json"))
    whl = next(u for u in info["urls"] if u["packagetype"] == "bdist_wheel" and u["filename"].endswith("-none-any.whl"))
    if not whl["url"].startswith("https://files.pythonhosted.org/"):  # PyPI serwuje pliki tylko stąd
        raise ValueError(f"nieoczekiwany adres pakietu: {whl['url']}")
    dane = _pobierz(whl["url"])
    if hashlib.sha256(dane).hexdigest() != whl["digests"]["sha256"]:
        raise ValueError(f"zła suma kontrolna {whl['filename']}")
    # od razu do docelowego, unikalnego katalogu - bez zmiany nazwy na końcu, bo antywirus skanujący świeże
    # pliki potrafi ją zablokować ("Odmowa dostępu"). Aktywny staje się dopiero po wpisaniu do STAN.
    cel = FOLDER / f"{pakiet}-{wer}-{os.getpid()}"
    try:
        zipfile.ZipFile(io.BytesIO(dane)).extractall(cel)
        compileall.compile_dir(cel, quiet=1)  # od razu .pyc - pierwsze pobieranie po aktualizacji bez czekania
    except BaseException:
        shutil.rmtree(cel, ignore_errors=True)
        raise
    return cel


def _posprzataj(stan: dict[str, str], starsze_niz_s: float = 0):
    """Usuwa katalogi pakietów, których STAN nie używa (to, czego używa działający proces, może być
    zablokowane - wtedy zniknie przy następnej okazji)."""
    teraz = time.time()
    for katalog in FOLDER.iterdir():
        if (katalog.is_dir() and str(katalog) not in stan.values()
                and teraz - katalog.stat().st_mtime >= starsze_niz_s):
            shutil.rmtree(katalog, ignore_errors=True)


def _wymagany_ejs(katalog_ytdlp: Path) -> str | None:
    for meta in katalog_ytdlp.glob("yt_dlp-*.dist-info/METADATA"):
        znalezione = re.search(r"^Requires-Dist: yt-dlp-ejs==([\w.]+)", meta.read_text(encoding="utf-8"), re.M)
        if znalezione:
            return znalezione.group(1)
    return None


def _sprawdz_w_procesie(exe: list[str], stan: dict[str, str]) -> dict:
    """Uruchamia exe --wersje z kandydatem na sys.path - importy muszą przejść w czystym procesie."""
    env = {**os.environ, ZMIENNA_TESTU: json.dumps(stan)}
    r = subprocess.run([*exe, "--wersje"], capture_output=True, text=True, encoding="utf-8", env=env,
                       timeout=120, creationflags=BEZ_OKNA)
    return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {}


def wersje_importem() -> dict:
    """Dla --wersje: importuje to, czego używa program (także moduł YouTube, największy i najczęściej zmieniany)."""
    import yt_dlp.extractor.youtube  # noqa: F401
    import yt_dlp_ejs  # noqa: F401
    import spotapi  # noqa: F401
    import ytmusicapi  # noqa: F401
    return {p: wersja(p) for p in (*PAKIETY, "yt-dlp-ejs")}


def aktualizuj(exe: list[str]) -> dict[str, str]:
    """Sprawdza PyPI i instaluje nowsze wersje. Zwraca {pakiet: nowa_wersja} - puste, gdy nic nie zmieniono.

    Każdy błąd (brak internetu, blokada PyPI, zepsuta wersja) = zostajemy przy tym, co działa.
    """
    FOLDER.mkdir(parents=True, exist_ok=True)
    stan = _wczytaj_stan()
    _posprzataj(stan, starsze_niz_s=3600)  # resztki po przerwanej aktualizacji; świeże może właśnie robić drugie okno
    nowy = dict(stan)
    oczekiwane = {}
    for pakiet in PAKIETY:
        najnowsza = _najnowsza(pakiet)
        if _jako_liczby(najnowsza) <= _jako_liczby(wersja(pakiet)):
            continue
        katalog = _rozpakuj_wheel(pakiet, najnowsza)
        nowy[pakiet] = str(katalog)
        oczekiwane[pakiet] = najnowsza
        if pakiet == "yt-dlp":
            ejs = _wymagany_ejs(katalog)
            if ejs and ejs != wersja("yt-dlp-ejs"):
                nowy["yt-dlp-ejs"] = str(_rozpakuj_wheel("yt-dlp-ejs", ejs))
                oczekiwane["yt-dlp-ejs"] = ejs
    if not oczekiwane:
        return {}

    wynik = _sprawdz_w_procesie(exe, nowy)
    if any(wynik.get(p) != w for p, w in oczekiwane.items()):
        # nowa wersja nie wstaje w tym exe (np. potrzebuje czegoś, czego nie spakowaliśmy) - wycofujemy
        for p in oczekiwane:
            shutil.rmtree(nowy[p], ignore_errors=True)
        raise RuntimeError(f"aktualizacja {oczekiwane} nie przeszła testu: {wynik}")

    tymczasowy = STAN.with_suffix(".tmp")
    tymczasowy.write_text(json.dumps(nowy, indent=1), encoding="utf-8")
    os.replace(tymczasowy, STAN)
    _posprzataj(nowy)
    zastosuj()  # ten proces (okno) też od razu widzi nowe wersje - m.in. wyszukiwarka, jeśli jeszcze nie ruszała
    return oczekiwane
