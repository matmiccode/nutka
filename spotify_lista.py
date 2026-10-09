"""Spotify -> lista utworów -> dopasowanie w YouTube Music (MATCODE).

Ze Spotify bierzemy wyłącznie dane (tytuł, wykonawcy, album, długość, okładka) - przez spotapi, czyli to samo
publiczne API, z którego korzysta odtwarzacz w przeglądarce: bez konta, bez kluczy, ~5 s na stronę 343 utworów.
(spotDL robił to przez współdzielone klucze API, które Spotify mocno przycina: album 10 utworów = 2 minuty.)
Dźwięk zawsze pochodzi z YouTube Music - dopasowanie po wykonawcy, tytule i długości (dopasuj()).
"""

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from teksty import t


@dataclass
class Utwor:
    tytul: str
    wykonawcy: list[str]
    album: str
    sekundy: int
    spotify_id: str
    okladka: str = ""           # adres największej okładki albumu (i.scdn.co)
    wykonawca_albumu: str = ""
    rok: str = ""
    numer: int = 0              # numer utworu na albumie (0 = nie numerujemy pliku)
    youtube_id: str = ""        # wypełnia dopasuj()

    @property
    def wykonawca(self) -> str:
        return ", ".join(self.wykonawcy)

    @property
    def czas(self) -> str:
        return f"{self.sekundy // 60}:{self.sekundy % 60:02d}"


@dataclass
class Lista:
    nazwa: str
    rodzaj: str                 # "utwór" | "album" | "playlista"
    utwory: list[Utwor] = field(default_factory=list)


def rozpoznaj(link: str) -> tuple[str, str] | None:
    """('track'|'album'|'playlist', id) z linku open.spotify.com/... albo spotify:...:..."""
    znalezione = re.search(r"(track|album|playlist)[/:]([A-Za-z0-9]{22})", link)
    return (znalezione.group(1), znalezione.group(2)) if znalezione else None


# ---------- odczyt ze Spotify ----------

def _okladka(cover_art: dict | None) -> str:
    zrodla = (cover_art or {}).get("sources") or []
    return max(zrodla, key=lambda z: z.get("width") or 0)["url"] if zrodla else ""


def _nazwy(artysci: dict | None) -> list[str]:
    return [a["profile"]["name"] for a in (artysci or {}).get("items", []) if a.get("profile")]


def _id(uri: str) -> str:
    return uri.rsplit(":", 1)[-1]


def wczytaj(link: str) -> Lista:
    """Utwór, album albo cała playlista (stronicowanie po 343) - same dane, nic nie pobiera."""
    from spotapi import PublicAlbum, PublicPlaylist
    from spotapi.public import Public

    rodzaj, ident = rozpoznaj(link) or (None, None)
    if rodzaj == "playlist":
        playlista = PublicPlaylist(ident)
        pierwsza = playlista.get_playlist_info(limit=343)["data"]["playlistV2"]
        lista = Lista(pierwsza.get("name") or "Playlista", "playlista")
        for strona in playlista.paginate_playlist():
            for element in strona.get("items", []):
                dane = (element.get("itemV2") or {}).get("data") or {}
                if dane.get("__typename") != "Track" or not dane.get("name"):
                    continue  # podcasty, utwory usunięte ze Spotify
                album = dane.get("albumOfTrack") or {}
                lista.utwory.append(Utwor(
                    tytul=dane["name"], wykonawcy=_nazwy(dane.get("artists")), album=album.get("name", ""),
                    sekundy=round((dane.get("trackDuration") or {}).get("totalMilliseconds", 0) / 1000),
                    spotify_id=_id(dane.get("uri", "")), okladka=_okladka(album.get("coverArt")),
                    wykonawca_albumu=", ".join(_nazwy(album.get("artists"))),
                    rok=((album.get("date") or {}).get("isoString") or "")[:4]))
        return lista

    if rodzaj == "album":
        album = PublicAlbum(ident).get_album_info(limit=343)["data"]["albumUnion"]
        okladka, wykonawca_albumu = _okladka(album.get("coverArt")), ", ".join(_nazwy(album.get("artists")))
        rok = ((album.get("date") or {}).get("isoString") or "")[:4]
        lista = Lista(album.get("name") or "Album", "album")
        for element in (album.get("tracksV2") or {}).get("items", []):
            utwor = element.get("track") or {}
            lista.utwory.append(Utwor(
                tytul=utwor.get("name", ""), wykonawcy=_nazwy(utwor.get("artists")), album=album.get("name", ""),
                sekundy=round((utwor.get("duration") or {}).get("totalMilliseconds", 0) / 1000),
                spotify_id=_id(utwor.get("uri", "")), okladka=okladka, wykonawca_albumu=wykonawca_albumu,
                rok=rok, numer=utwor.get("trackNumber") or 0))
        return lista

    if rodzaj == "track":
        utwor = Public.song_info(ident)["data"]["trackUnion"]
        album = utwor.get("albumOfTrack") or {}
        wykonawcy = _nazwy(utwor.get("firstArtist")) + _nazwy(utwor.get("otherArtists"))
        u = Utwor(tytul=utwor.get("name", ""), wykonawcy=wykonawcy or _nazwy(utwor.get("artists")),
                  album=album.get("name", ""),
                  sekundy=round((utwor.get("duration") or {}).get("totalMilliseconds", 0) / 1000),
                  spotify_id=ident, okladka=_okladka(album.get("coverArt")),
                  wykonawca_albumu=", ".join(_nazwy(album.get("artists"))),
                  rok=((album.get("date") or {}).get("isoString") or "")[:4])
        return Lista(u.tytul, "utwór", [u])

    raise ValueError(t("To nie jest link do utworu, albumu ani playlisty Spotify."))


# ---------- dopasowanie w YouTube Music ----------

def _norm(tekst: str) -> str:
    """Do porównań: małe litery, bez polskich znaków, bez dopisków typu (feat. …), - Remastered 2011."""
    tekst = unicodedata.normalize("NFKD", tekst.lower()).encode("ascii", "ignore").decode()
    tekst = re.sub(r"[(\[].*?[)\]]", " ", tekst)
    tekst = re.sub(r"\s-\s.*(remaster|version|wersja|edit|mix|live).*$", " ", tekst)
    tekst = re.sub(r"\b(feat|ft)\.?\b.*$", " ", tekst)
    return re.sub(r"[^a-z0-9]+", " ", tekst).strip()


def _podobienstwo(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _ocena(utwor: Utwor, wynik: dict, tolerancja_s: int) -> float:
    """0 = odrzucony; im więcej, tym lepiej. Długość jest najmocniejszym sygnałem (inna wersja = inna długość)."""
    roznica = abs((wynik.get("duration_seconds") or 0) - utwor.sekundy)
    if not wynik.get("videoId") or roznica > tolerancja_s:
        return 0.0
    tytul = _podobienstwo(utwor.tytul, wynik.get("title", ""))
    artysci_wyniku = " ".join(a.get("name", "") for a in wynik.get("artists") or [])
    artysta = max((_podobienstwo(w, artysci_wyniku) for w in utwor.wykonawcy), default=0.0)
    if tytul < 0.6 or artysta < 0.5:
        return 0.0
    return tytul * 2 + artysta + (1 - roznica / (tolerancja_s + 1))


def dopasuj(utwor: Utwor, klient) -> str | None:
    """videoId z YouTube Music: najpierw oficjalne utwory, potem filmy; None = nic pewnego."""
    zapytanie = f"{utwor.wykonawcy[0] if utwor.wykonawcy else ''} {utwor.tytul}".strip()
    for filtr, tolerancja in (("songs", 7), ("videos", 15)):
        wyniki = klient.search(zapytanie, filter=filtr, limit=10)[:10]
        najlepszy = max(wyniki, key=lambda w: _ocena(utwor, w, tolerancja), default=None)
        if najlepszy and _ocena(utwor, najlepszy, tolerancja) > 0:
            utwor.youtube_id = najlepszy["videoId"]
            return utwor.youtube_id
    return None


# ---------- pliki ----------

_ZASTRZEZONE = re.compile(r"(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$")  # nazwy urządzeń Windows


def bezpieczna_nazwa(tekst: str) -> str:
    """Składnik ścieżki z nazwy z internetu: bez znaków zabronionych w Windows, bez kropek i spacji na końcach
    (Win32 je ignoruje, więc „.. ” wskazywałoby katalog nadrzędny) i bez nazw urządzeń (CON, NUL…)."""
    tekst = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", tekst).strip(" .")[:150].rstrip(" .") or "bez nazwy"
    return "_" + tekst if _ZASTRZEZONE.match(tekst) else tekst


def sciezka_pliku(utwor: Utwor, lista: Lista, folder: Path) -> Path:
    """Stała nazwa pliku = rozpoznawanie, co już masz (synchronizacja playlisty).
    Album: podfolder + numer utworu; playlista: podfolder bez numerów (kolejność w playliście się zmienia)."""
    nazwa = bezpieczna_nazwa(f"{utwor.wykonawcy[0] if utwor.wykonawcy else t('Nieznany')} - {utwor.tytul}")
    if lista.rodzaj == "utwór":
        plik = folder / f"{nazwa}.mp3"
    else:
        if lista.rodzaj == "album" and utwor.numer:
            nazwa = f"{utwor.numer:02d} - {nazwa}"
        plik = folder / bezpieczna_nazwa(lista.nazwa) / f"{nazwa}.mp3"
    if not plik.resolve().is_relative_to(folder.resolve()):  # pas bezpieczeństwa - bezpieczna_nazwa() to gwarantuje
        raise ValueError(f"ścieżka poza folderem docelowym: {plik}")
    return plik


def otaguj(plik: Path, utwor: Utwor, lista: Lista):
    """Tagi ze Spotify (dokładniejsze niż z YouTube) + okładka albumu."""
    import urllib.parse
    import urllib.request

    from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2, TRCK, ID3NoHeaderError

    try:
        tagi = ID3(plik)
    except ID3NoHeaderError:
        tagi = ID3()
    tagi.delall("APIC")
    tagi.add(TIT2(encoding=3, text=utwor.tytul))
    tagi.add(TPE1(encoding=3, text=utwor.wykonawcy or [""]))
    tagi.add(TALB(encoding=3, text=utwor.album))
    if utwor.wykonawca_albumu:
        tagi.add(TPE2(encoding=3, text=utwor.wykonawca_albumu))
    if utwor.rok:
        tagi.add(TDRC(encoding=3, text=utwor.rok))
    if utwor.numer:
        tagi.add(TRCK(encoding=3, text=str(utwor.numer)))
    adres = urllib.parse.urlsplit(utwor.okladka) if utwor.okladka else None
    # okładka tylko z CDN Spotify przez https - adres przychodzi z danych z sieci
    if adres and adres.scheme == "https" and (adres.hostname or "").endswith((".scdn.co", ".spotifycdn.com")):
        try:
            with urllib.request.urlopen(utwor.okladka, timeout=15) as odp:
                tagi.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=odp.read()))
        except OSError:
            pass  # bez okładki, ale plik jest
    tagi.save(plik, v2_version=3)
