"""Teksty piosenek z LRCLIB (teksty_piosenek.py) bez sieci - odpowiedzi LRCLIB podstawione funkcją.

Warunki odbioru:
- LRCLIB ma tekst z czasami -> mp3 dostaje zwykły tekst (USLT) i tekst z czasami (SYLT), obok mp3 powstaje .lrc;
- LRCLIB ma tylko zwykły tekst -> sam USLT, bez .lrc;
- brak tekstu, utwór instrumentalny albo błąd sieci -> plik bez zmian, bez .lrc i bez wyjątku;
- dokładne zapytanie (/api/get) nic nie dało -> wyszukiwanie: wynik o pasującej długości (±3 s), z czasami przed bez;
- tytuł filmu „Wykonawca - Tytuł (Official Video)” z nazwą kanału jako wykonawcą też znajduje tekst;
- drugi zapis nie dubluje tagów.
"""

import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import teksty_piosenek as tp

LRC = "[00:17.12] Małomiasteczkowa twarz\n[00:20.50] Małomiasteczkowa głowa\n[00:24.00] \n[01:02.75] Z małego miasta wielkie sny"
ZWYKLY = "Małomiasteczkowa twarz\nMałomiasteczkowa głowa\n\nZ małego miasta wielkie sny"


def wynik(**zmiany) -> dict:
    """Jedna pozycja w formacie LRCLIB."""
    dane = {"id": 1, "trackName": "Małomiasteczkowy", "artistName": "Dawid Podsiadło", "albumName": "Małomiasteczkowy",
            "duration": 203.0, "instrumental": False, "plainLyrics": ZWYKLY, "syncedLyrics": LRC}
    dane.update(zmiany)
    return dane


class AtrapaLrclib:
    """Zamiast sieci: /api/get zwraca `dokladny` (None = 404), /api/search zwraca `szukane`; zapamiętuje adresy."""

    def __init__(self, dokladny=None, szukane=()):
        self.dokladny, self.szukane, self.adresy = dokladny, list(szukane), []

    def __call__(self, adres: str):
        self.adres = adres
        self.adresy.append(adres)
        if "/api/get?" in adres:
            return self.dokladny
        if "/api/search?" in adres:
            return self.szukane
        raise AssertionError(adres)


class Linie(unittest.TestCase):
    def test_czasy_w_milisekundach(self):
        self.assertEqual(tp.linie(LRC), [(17120, "Małomiasteczkowa twarz"), (20500, "Małomiasteczkowa głowa"),
                                         (24000, ""), (62750, "Z małego miasta wielkie sny")])

    def test_kilka_czasow_w_jednej_linii_i_smieci(self):
        self.assertEqual(tp.linie("[ar:Ktoś]\n[00:01.00][00:30.5]Refren\nbez czasu\n[1:02]Krótki zapis"),
                         [(1000, "Refren"), (30500, "Refren"), (62000, "Krótki zapis")])


class Znajdz(unittest.TestCase):
    def test_dokladne_trafienie(self):
        lrclib = AtrapaLrclib(dokladny=wynik())
        slowa = tp.znajdz("Dawid Podsiadło", "Małomiasteczkowy", "Małomiasteczkowy", 204, pobierz=lrclib)
        self.assertEqual((slowa.zwykle, slowa.z_czasami), (ZWYKLY, LRC))
        czesci = urlsplit(lrclib.adresy[0])
        self.assertEqual((czesci.scheme, czesci.netloc, czesci.path), ("https", "lrclib.net", "/api/get"))
        self.assertEqual(parse_qs(czesci.query), {"artist_name": ["Dawid Podsiadło"], "track_name": ["Małomiasteczkowy"],
                                                  "album_name": ["Małomiasteczkowy"], "duration": ["204"]})

    def test_bez_albumu_od_razu_wyszukiwanie(self):
        lrclib = AtrapaLrclib(szukane=[wynik()])
        self.assertIsNotNone(tp.znajdz("Dawid Podsiadło", "Małomiasteczkowy", "", 203, pobierz=lrclib))
        self.assertTrue(all("/api/get?" not in a for a in lrclib.adresy))  # /api/get wymaga albumu

    def test_wyszukiwanie_wybiera_dlugosc_i_czasy(self):
        szukane = [wynik(id=1, duration=242.0),                    # inna wersja (dłuższa) - odpada
                   wynik(id=2, duration=204.0, syncedLyrics=None),  # pasuje, ale bez czasów
                   wynik(id=3, duration=202.0, plainLyrics="z czasami")]
        slowa = tp.znajdz("Dawid Podsiadło", "Małomiasteczkowy", "Inny album", 203, pobierz=AtrapaLrclib(szukane=szukane))
        self.assertEqual(slowa.zwykle, "z czasami")

    def test_zly_wykonawca_albo_tytul_odpada(self):
        szukane = [wynik(artistName="Ktoś Zupełnie Inny"), wynik(trackName="Całkiem inna piosenka")]
        self.assertIsNone(tp.znajdz("Dawid Podsiadło", "Małomiasteczkowy", "", 203, pobierz=AtrapaLrclib(szukane=szukane)))

    def test_instrumentalny_i_pusty(self):
        szukane = [wynik(instrumental=True, plainLyrics=None, syncedLyrics=None), wynik(plainLyrics="", syncedLyrics="")]
        self.assertIsNone(tp.znajdz("Dawid Podsiadło", "Małomiasteczkowy", "", 203, pobierz=AtrapaLrclib(szukane=szukane)))

    def test_tytul_filmu_z_kanalem(self):
        # zwykły film: wykonawca = nazwa kanału, tytuł = „Wykonawca - Tytuł (Official Video)”
        lrclib = AtrapaLrclib(szukane=[wynik()])
        slowa = tp.znajdz("SonyMusicPoland", "Dawid Podsiadło - Małomiasteczkowy (Official Video)", "", 203, pobierz=lrclib)
        self.assertIsNotNone(slowa)
        self.assertTrue(any("Official" not in a and "Ma%C5%82omiasteczkowy" in a for a in lrclib.adresy))

    def test_inna_dlugosc_sam_zwykly_tekst(self):
        # teledysk z intro jest dłuższy od utworu: czasy linijek by się rozjechały, ale słowa są te same
        szukane = [wynik(id=1, duration=300.0, plainLyrics="wersja live"), wynik(id=2, duration=203.0)]
        slowa = tp.znajdz("Dawid Podsiadło", "Małomiasteczkowy (Official Video)", "", 216,
                          pobierz=AtrapaLrclib(szukane=szukane))
        self.assertEqual((slowa.zwykle, slowa.z_czasami), (ZWYKLY, ""))  # najbliższa długość, bez czasów

    def test_tylko_zwykly_tekst_z_czasow(self):
        # LRCLIB bywa, że ma same czasy - zwykły tekst = linijki bez czasów
        slowa = tp.znajdz("Dawid Podsiadło", "Małomiasteczkowy", "", 203,
                          pobierz=AtrapaLrclib(szukane=[wynik(plainLyrics=None)]))
        self.assertEqual(slowa.zwykle, "Małomiasteczkowa twarz\nMałomiasteczkowa głowa\n\nZ małego miasta wielkie sny")


class Zapis(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.mp3 = self.folder / "Dawid Podsiadło - Małomiasteczkowy.mp3"
        self.mp3.write_bytes(b"")  # mutagen dopisze sam znacznik ID3 - dźwięk nie jest potrzebny

    def tagi(self):
        from mutagen.id3 import ID3
        return ID3(self.mp3)

    def test_z_czasami(self):
        tp.zapisz(self.mp3, tp.Slowa(ZWYKLY, LRC))
        tagi = self.tagi()
        self.assertEqual(tagi.getall("USLT")[0].text, ZWYKLY)
        self.assertEqual(tagi.getall("SYLT")[0].text[0], ("Małomiasteczkowa twarz", 17120))
        lrc = self.mp3.with_suffix(".lrc")
        self.assertEqual(lrc.read_text(encoding="utf-8"), LRC + "\n")
        self.assertFalse(lrc.read_bytes().startswith(b"\xef\xbb\xbf"))  # bez BOM, jak pliki z LRCGET

    def test_tylko_zwykly(self):
        tp.zapisz(self.mp3, tp.Slowa(ZWYKLY))
        self.assertEqual(self.tagi().getall("USLT")[0].text, ZWYKLY)
        self.assertEqual(self.tagi().getall("SYLT"), [])
        self.assertFalse(self.mp3.with_suffix(".lrc").exists())

    def test_drugi_zapis_nie_dubluje(self):
        tp.zapisz(self.mp3, tp.Slowa(ZWYKLY, LRC))
        tp.zapisz(self.mp3, tp.Slowa("nowy", LRC))
        self.assertEqual([u.text for u in self.tagi().getall("USLT")], ["nowy"])
        self.assertEqual(len(self.tagi().getall("SYLT")), 1)

    def test_dodaj_bez_tekstu_nic_nie_zmienia(self):
        self.assertFalse(tp.dodaj(self.mp3, "Ktoś", "Coś", pobierz=AtrapaLrclib()))
        self.assertEqual(self.mp3.read_bytes(), b"")
        self.assertFalse(self.mp3.with_suffix(".lrc").exists())

    def test_dodaj_blad_sieci_bez_wyjatku(self):
        def bez_sieci(_adres):
            raise OSError("brak internetu")
        self.assertFalse(tp.dodaj(self.mp3, "Dawid Podsiadło", "Małomiasteczkowy", "Album", 203, pobierz=bez_sieci))
        self.assertEqual(self.mp3.read_bytes(), b"")

    def test_dodaj_z_tagow(self):
        # pojedynczy utwór z YouTube: wykonawca, tytuł i album z tagów, które wpisał yt-dlp
        from mutagen.id3 import ID3, TALB, TIT2, TPE1
        tagi = ID3()
        tagi.add(TIT2(encoding=3, text="Małomiasteczkowy"))
        tagi.add(TPE1(encoding=3, text="Dawid Podsiadło"))
        tagi.add(TALB(encoding=3, text="Małomiasteczkowy"))
        tagi.save(self.mp3)
        lrclib = AtrapaLrclib(szukane=[wynik()])
        self.assertTrue(tp.dodaj_z_tagow(self.mp3, pobierz=lrclib))
        self.assertTrue(self.mp3.with_suffix(".lrc").exists())
        self.assertEqual(self.tagi().getall("TIT2")[0].text, ["Małomiasteczkowy"])  # reszta tagów zostaje


class Agent(unittest.TestCase):
    def test_naglowek_programu(self):
        # LRCLIB prosi, żeby programy przedstawiały się w User-Agent
        self.assertTrue(tp.AGENT.startswith("Nutka"))
        self.assertIn("github.com/matmiccode/nutka", tp.AGENT)


if __name__ == "__main__":
    unittest.main()
