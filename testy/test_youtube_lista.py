"""Playlista/album z YouTube w trybie listy: youtube_lista.z_danych na JSON-ie jak z yt-dlp --flat-playlist -J,
ścieżki mp4 (spotify_lista.sciezka_pliku) i komendy yt-dlp dla jednej pozycji (app.komenda_utworu/komenda_wideo)."""

import unittest
from pathlib import Path

import app
import spotify_lista as sl
import youtube_lista


def wpis(ident: str, tytul: str, kanal: str | None = "Dawid Podsiadło", sekundy: int | None = 200) -> dict:
    return {"id": ident, "title": tytul, "channel": kanal, "uploader": kanal, "duration": sekundy, "_type": "url"}


ALBUM = {"title": "Album - Małomiasteczkowy", "release_year": 2018, "channel": None,
         "entries": [wpis("a1", "Cantate Tutti", sekundy=187), wpis("a2", "Dżins", sekundy=312),
                     wpis("a3", "Nie - Ma Fal", sekundy=239)]}  # myślnik w tytule utworu z albumu zostaje
PLAYLISTA = {"title": "  DAWID PODSIADŁO ", "release_year": None, "channel": "Damian Lichon",
             "entries": [wpis("p1", "Nie Ma Fal"),
                         wpis("p2", "Dawid Podsiadło - Małomiasteczkowy (Official Video)", kanal="SonyMusicPoland"),
                         wpis("p3", "[Private video]", kanal=None, sekundy=None),
                         wpis("p4", "[Deleted video]"),
                         {"id": "", "title": "bez identyfikatora"},
                         wpis("p6", "Launch", kanal="NASA - Topic", sekundy=None)]}


class ZDanych(unittest.TestCase):
    def test_album(self):
        lista = youtube_lista.z_danych(ALBUM)
        self.assertEqual((lista.rodzaj, lista.nazwa, lista.zrodlo), ("album", "Małomiasteczkowy", "youtube"))
        self.assertEqual([u.youtube_id for u in lista.utwory], ["a1", "a2", "a3"])
        self.assertEqual([u.numer for u in lista.utwory], [1, 2, 3])
        u = lista.utwory[2]
        self.assertEqual((u.tytul, u.wykonawcy, u.album, u.rok, u.sekundy), ("Nie - Ma Fal", ["Dawid Podsiadło"],
                                                                             "Małomiasteczkowy", "2018", 239))
        self.assertEqual(u.wykonawca_albumu, "Dawid Podsiadło")
        self.assertEqual(u.spotify_id, "")
        self.assertEqual(u.czas, "3:59")

    def test_playlista(self):
        lista = youtube_lista.z_danych(PLAYLISTA)
        self.assertEqual((lista.rodzaj, lista.nazwa), ("playlista", "DAWID PODSIADŁO"))
        self.assertEqual([u.youtube_id for u in lista.utwory], ["p1", "p2", "p6"])  # prywatne, usunięte, bez id - nie
        p1, p2, p6 = lista.utwory
        self.assertEqual((p1.tytul, p1.wykonawcy), ("Nie Ma Fal", ["Dawid Podsiadło"]))
        # teledysk „Wykonawca - Tytuł” na kanale wytwórni: wykonawca z tytułu, nie z kanału
        self.assertEqual((p2.tytul, p2.wykonawcy), ("Małomiasteczkowy (Official Video)", ["Dawid Podsiadło"]))
        self.assertEqual((p6.tytul, p6.wykonawcy, p6.sekundy), ("Launch", ["NASA"], 0))  # „- Topic” odcięte
        for u in lista.utwory:
            self.assertEqual((u.numer, u.album, u.rok, u.wykonawca_albumu), (0, "", "", ""))

    def test_przedrostki_i_puste(self):
        for tytul, rodzaj, nazwa in (("Single - Sezon", "album", "Sezon"), ("EP - Ep", "album", "Ep"),
                                     ("Album - Sezon 2 ", "album", "Sezon 2"), ("", "playlista", "Playlista"),
                                     ("Albumy lata", "playlista", "Albumy lata"), ("Album-x", "playlista", "Album-x")):
            with self.subTest(tytul=tytul):
                lista = youtube_lista.z_danych({"title": tytul, "entries": []})
                self.assertEqual((lista.rodzaj, lista.nazwa, len(lista.utwory)), (rodzaj, nazwa, 0))
        self.assertEqual(youtube_lista.z_danych({}).utwory, [])

    def test_kanal_bez_nazwy(self):
        lista = youtube_lista.z_danych({"title": "x", "entries": [wpis("k1", "Tytuł", kanal=None)]})
        self.assertEqual(lista.utwory[0].wykonawcy, [])
        self.assertEqual(lista.utwory[0].wykonawca, "")


class Sciezki(unittest.TestCase):
    def test_mp4_w_folderze_filmow(self):
        lista = youtube_lista.z_danych(PLAYLISTA)
        folder = Path("C:/Users/Ty/Videos/Pobrane")
        self.assertEqual(sl.sciezka_pliku(lista.utwory[1], lista, folder, "mp4"),
                         folder / "DAWID PODSIADŁO" / "Dawid Podsiadło - Małomiasteczkowy (Official Video).mp4")
        self.assertEqual(sl.sciezka_pliku(lista.utwory[1], lista, folder).suffix, ".mp3")  # domyślnie mp3

    def test_album_z_numerami(self):
        lista = youtube_lista.z_danych(ALBUM)
        folder = Path("C:/Users/Ty/Music/Pobrane")
        self.assertEqual(sl.sciezka_pliku(lista.utwory[0], lista, folder),
                         folder / "Małomiasteczkowy" / "01 - Dawid Podsiadło - Cantate Tutti.mp3")


class Komendy(unittest.TestCase):
    plik = Path("C:/Users/Ty/Videos/Pobrane/Lista/Kanał - 100% Tytuł.mp4")

    def test_wideo(self):
        k = app.komenda_wideo("abc123XYZ-_", self.plik, "720p")
        self.assertEqual(k[-2:], ["--", "https://www.youtube.com/watch?v=abc123XYZ-_"])
        self.assertEqual(k[k.index("-S") + 1], app.JAKOSCI_WIDEO["720p"])
        self.assertEqual(k[k.index("--merge-output-format") + 1], "mp4")
        szablon = k[k.index("-o") + 1]
        self.assertTrue(szablon.endswith(".%(ext)s"), szablon)
        self.assertIn("100%% Tytuł", szablon)
        for opcja in ("--ignore-config", "--no-playlist", "--embed-metadata", "--progress-template"):
            self.assertIn(opcja, k)
        self.assertNotIn("--embed-thumbnail", k)  # w mp4 okładka byłaby drugą ścieżką obrazu
        self.assertNotIn("-x", k)
        with self.assertRaises(KeyError):
            app.komenda_wideo("abc", self.plik, "4K")

    def test_utwor_z_okladka(self):
        bez = app.komenda_utworu("abc", self.plik)
        z = app.komenda_utworu("abc", self.plik, z_okladka=True)
        self.assertNotIn("--embed-thumbnail", bez)  # Spotify: okładkę i tagi dopisze otaguj()
        self.assertIn("--embed-thumbnail", z)
        self.assertIn("--embed-metadata", z)
        self.assertEqual(bez[-2:], z[-2:])
        self.assertIn("-x", z)


if __name__ == "__main__":
    unittest.main()
