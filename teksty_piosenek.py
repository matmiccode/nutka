"""Teksty piosenek z LRCLIB (https://lrclib.net) - otwarta, społecznościowa baza tekstów, bez kluczy i kont (MATCODE).

Do mp3 trafia zwykły tekst (tag USLT - pokazuje go prawie każdy odtwarzacz) i tekst z czasami linijek (tag SYLT),
a obok mp3 plik .lrc o tej samej nazwie - z niego tekst przewijany w rytm piosenki biorą odtwarzacze, np. Poweramp
na telefonie, AIMP i MusicBee na PC. Brak tekstu albo brak sieci = plik bez tekstu, pobieranie się nie psuje.

Do LRCLIB idą tylko dane utworu: wykonawca, tytuł, album i długość.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from spotify_lista import _podobienstwo

ADRES = "https://lrclib.net/api/"
# LRCLIB prosi, żeby programy przedstawiały się nazwą i stroną; app.py dopisuje wersję
AGENT = "Nutka (https://github.com/matmiccode/nutka)"
TOLERANCJA_S = 3  # inna długość = inna wersja utworu (radio edit, live) - czasy linijek by się rozjechały
_CZAS = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


@dataclass
class Slowa:
    zwykle: str
    z_czasami: str = ""  # format LRC: „[01:02.34] linijka”


def linie(lrc: str) -> list[tuple[int, str]]:
    """Tekst LRC -> [(milisekundy, linijka)] po kolei; linie bez czasu (np. [ar:…]) pomija."""
    wynik = []
    for linia in lrc.splitlines():
        czasy, reszta = [], linia.strip()
        while m := _CZAS.match(reszta):
            czasy.append(round((int(m[1]) * 60 + float(m[2])) * 1000))
            reszta = reszta[m.end():]
        wynik += [(ms, reszta.strip()) for ms in czasy]
    return sorted(wynik, key=lambda para: para[0])


def _pobierz_json(adres: str):
    """JSON z LRCLIB; None = 404 (nie ma takiego utworu)."""
    zadanie = urllib.request.Request(adres, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(zadanie, timeout=10) as odp:
            return json.load(odp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _slowa(wynik: dict | None) -> Slowa | None:
    if not wynik or wynik.get("instrumental"):
        return None
    z_czasami = (wynik.get("syncedLyrics") or "").strip()
    zwykle = (wynik.get("plainLyrics") or "").strip() or "\n".join(tekst for _, tekst in linie(z_czasami)).strip()
    return Slowa(zwykle, z_czasami) if zwykle else None


def _ocena(wynik: dict, wykonawca: str, tytul: str, sekundy: int) -> float:
    """0 = odrzucony; im więcej, tym lepiej. Długość jak przy dopasowaniu w YouTube Music, tekst z czasami wygrywa."""
    if not _slowa(wynik):
        return 0.0
    if sekundy and abs((wynik.get("duration") or 0) - sekundy) > TOLERANCJA_S:
        return 0.0
    zgodnosc_tytulu = _podobienstwo(tytul, wynik.get("trackName") or "")
    zgodnosc_wykonawcy = _podobienstwo(wykonawca, wynik.get("artistName") or "")
    if zgodnosc_tytulu < 0.6 or zgodnosc_wykonawcy < 0.5:
        return 0.0
    return zgodnosc_tytulu * 2 + zgodnosc_wykonawcy + (1 if wynik.get("syncedLyrics") else 0)


def _warianty(wykonawca: str, tytul: str) -> list[tuple[str, str]]:
    """Kogo i czego szukać. Zwykły film: wykonawca bywa nazwą kanału, a prawdziwy jest w tytule „Wykonawca - Tytuł”.
    Dopiski w nawiasach („(Official Video)”) tylko przeszkadzają wyszukiwarce."""
    czysty = re.sub(r"\s*[(\[].*?[)\]]", "", tytul).strip() or tytul
    warianty = [(wykonawca, czysty)]
    przed, _, po = czysty.partition(" - ")
    if przed.strip() and po.strip():
        warianty.append((przed.strip(), po.strip()))
    return warianty


def znajdz(wykonawca: str, tytul: str, album: str = "", sekundy: int = 0, pobierz=_pobierz_json) -> Slowa | None:
    """Najpierw dokładne zapytanie (wymaga albumu i długości), potem wyszukiwanie i wybór najlepszej pozycji.
    Nic o zgodnej długości (np. teledysk z intro) = zwykły tekst z najbliższej długości, bez czasów linijek."""
    if wykonawca and tytul and album and sekundy:
        slowa = _slowa(pobierz(ADRES + "get?" + urllib.parse.urlencode(
            {"artist_name": wykonawca, "track_name": tytul, "album_name": album, "duration": int(sekundy)})))
        if slowa:
            return slowa
    zebrane = []  # (ocena bez długości, różnica długości, wynik) - na wypadek, gdy żadna długość nie pasuje
    for kto, co in _warianty(wykonawca, tytul):
        zapytania = [{"track_name": co, "artist_name": kto}, {"q": f"{kto} {co}"}] if kto else [{"q": co}]
        for zapytanie in zapytania:
            wyniki = pobierz(ADRES + "search?" + urllib.parse.urlencode(zapytanie)) or []
            najlepszy = max(wyniki, key=lambda w: _ocena(w, kto, co, sekundy), default=None)
            if najlepszy and _ocena(najlepszy, kto, co, sekundy) > 0:
                return _slowa(najlepszy)
            zebrane += [(ocena, abs((w.get("duration") or 0) - sekundy), w)
                        for w in wyniki if (ocena := _ocena(w, kto, co, 0)) > 0]
    if zebrane:
        _, _, najblizszy = min(zebrane, key=lambda z: (z[1], -z[0]))
        return Slowa(_slowa(najblizszy).zwykle)
    return None


def zapisz(plik: Path, slowa: Slowa):
    """USLT (+ SYLT i plik .lrc obok, gdy są czasy linijek). Pozostałe tagi zostają."""
    from mutagen.id3 import ID3, SYLT, USLT, ID3NoHeaderError

    try:
        tagi = ID3(plik)
    except ID3NoHeaderError:
        tagi = ID3()
    tagi.delall("USLT")
    tagi.delall("SYLT")
    tagi.add(USLT(encoding=3, lang="XXX", desc="", text=slowa.zwykle))
    if slowa.z_czasami:
        # format=2: czas w milisekundach, type=1: słowa piosenki
        tagi.add(SYLT(encoding=3, lang="XXX", format=2, type=1, desc="",
                      text=[(tekst, ms) for ms, tekst in linie(slowa.z_czasami)]))
    tagi.save(plik, v2_version=3)
    if slowa.z_czasami:
        # UTF-8 bez BOM - tak zapisuje LRCGET (program twórców LRCLIB) i tak czytają odtwarzacze
        plik.with_suffix(".lrc").write_text(slowa.z_czasami.strip() + "\n", encoding="utf-8", newline="\n")


def dodaj(plik: Path, wykonawca: str, tytul: str, album: str = "", sekundy: int = 0,
          pobierz=_pobierz_json) -> Slowa | None:
    """Znajdź i zapisz; zwraca zapisany tekst albo None. Nigdy nie przerywa pobierania - każdy błąd to po prostu
    brak tekstu."""
    try:
        slowa = znajdz(wykonawca, tytul, album, sekundy, pobierz)
        if slowa:
            zapisz(plik, slowa)
        return slowa
    except Exception:
        return None


def dodaj_z_tagow(plik: Path, pobierz=_pobierz_json) -> Slowa | None:
    """Pojedynczy utwór z YouTube: kogo i czego szukać - z tagów, które wpisał yt-dlp, długość z samego mp3."""
    try:
        from mutagen.id3 import ID3
        from mutagen.mp3 import MP3

        tagi = ID3(plik)

        def tag(nazwa: str) -> str:
            ramka = tagi.get(nazwa)
            return str(ramka.text[0]).strip() if ramka and ramka.text else ""
        try:
            sekundy = round(MP3(plik).info.length)
        except Exception:
            sekundy = 0  # bez długości szukamy tylko po nazwach
        return dodaj(plik, tag("TPE1"), tag("TIT2"), tag("TALB"), sekundy, pobierz)
    except Exception:
        return None
