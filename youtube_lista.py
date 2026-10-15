"""YouTube -> lista pozycji z playlisty albo albumu (MATCODE).

Spis bierze yt-dlp z opcją --flat-playlist (-J): w ~2 s tytuły, długości, kanały i identyfikatory wszystkich
pozycji bez wchodzenia na strony filmów - tak samo dla albumów i playlist YouTube Music, jak i zwykłych playlist
YouTube. Z tego powstaje ta sama Lista co ze Spotify (spotify_lista.py), więc okno pokazuje ją w tym samym
trybie listy: ptaszki, „masz już”, pobieranie po kilka naraz - w trybie „Muzyka” jako mp3, w „Wideo” jako mp4.
Samo wywołanie yt-dlp jest w app.py (lista_youtube()); tu tylko czyste przetwarzanie JSON-u (testy bez sieci).
"""

import re

from spotify_lista import Lista, Utwor
from teksty import t

# YouTube Music nazywa playlisty albumów "Album - Tytuł", "Single - Tytuł", "EP - Tytuł"
_PRZEDROSTEK_ALBUMU = re.compile(r"^(Album|Single|EP) - ")
# pozycje, których nie da się pobrać - YouTube pokazuje je w playliście pod takimi tytułami
_NIEDOSTEPNE = {"[Private video]", "[Deleted video]", "[Unavailable video]"}


def z_danych(dane: dict) -> Lista:
    """Lista z JSON-u yt-dlp (--flat-playlist -J). Album (przedrostek w tytule) dostaje numery utworów, rok
    i wykonawcę albumu. W playliście tytuł „Wykonawca - Tytuł” rozdzielamy na wykonawcę i tytuł (tak nazywają się
    teledyski), inaczej wykonawcą jest kanał (dla utworów YouTube Music kanał = artysta)."""
    tytul = (dane.get("title") or "").strip()
    album = bool(_PRZEDROSTEK_ALBUMU.match(tytul))
    nazwa = _PRZEDROSTEK_ALBUMU.sub("", tytul).strip() or (t("Album") if album else t("Playlista"))
    rok = str(dane.get("release_year") or "") if album else ""
    lista = Lista(nazwa, "album" if album else "playlista", zrodlo="youtube")
    for wpis in dane.get("entries") or []:
        ident, tytul_wpisu = wpis.get("id") or "", (wpis.get("title") or "").strip()
        if not ident or not tytul_wpisu or tytul_wpisu in _NIEDOSTEPNE:
            continue
        kanal = _bez_topic(wpis.get("channel") or wpis.get("uploader") or "")
        wykonawca, _, reszta = tytul_wpisu.partition(" - ")
        if reszta.strip() and wykonawca.strip() and not album:
            wykonawcy, tytul_utworu = [wykonawca.strip()], reszta.strip()
        else:
            wykonawcy, tytul_utworu = ([kanal] if kanal else []), tytul_wpisu
        lista.utwory.append(Utwor(
            tytul=tytul_utworu, wykonawcy=wykonawcy, album=nazwa if album else "",
            sekundy=int(wpis.get("duration") or 0), spotify_id="", rok=rok,
            numer=len(lista.utwory) + 1 if album else 0, youtube_id=ident))
    if album and lista.utwory:
        wykonawca_albumu = lista.utwory[0].wykonawca  # kanał pierwszego utworu = artysta albumu
        for utwor in lista.utwory:
            utwor.wykonawca_albumu = wykonawca_albumu
    return lista


def wiersz_filmu(dane: dict, link: str) -> dict:
    """Jeden film/utwór (JSON z yt-dlp -J) jako wiersz tabeli wyników - klucze jak w app.szukaj_yt_music():
    tytuł utworu (gdy YouTube Music go zna) albo filmu, wykonawca (artyści albo kanał), album, czas, link."""
    sekundy = int(dane.get("duration") or 0)
    wykonawca = ", ".join(dane.get("artists") or []) or _bez_topic(dane.get("channel") or dane.get("uploader") or "")
    return {"tytul": dane.get("track") or dane.get("title") or "", "wykonawca": wykonawca,
            "album": dane.get("album") or "", "czas": f"{sekundy // 60}:{sekundy % 60:02d}" if sekundy else "",
            "link": link}


def _bez_topic(kanal: str) -> str:
    """Kanały utworów YouTube Music nazywają się „Wykonawca - Topic”."""
    return re.sub(r"\s*-\s*Topic$", "", kanal).strip()
