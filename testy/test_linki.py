"""Linki i komendy yt-dlp (app.py): rozpoznawanie źródła, budowa komendy, znaczniki postępu.

Wklejony tekst trafia do yt-dlp jako argument - stąd nacisk na to, czego NIE wolno uznać za link."""

import unittest
from pathlib import Path

import app


class RozpoznajZrodlo(unittest.TestCase):
    def test_youtube(self):
        for link in ("https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                     "http://youtube.com/watch?v=x",
                     "https://m.youtube.com/watch?v=x",
                     "https://music.youtube.com/playlist?list=OLAK5uy_abc",
                     "https://youtu.be/dQw4w9WgXcQ",
                     "youtu.be/dQw4w9WgXcQ",                      # bez schematu
                     "  https://www.youtube.com/watch?v=x  ",      # spacje z obu stron
                     "HTTPS://WWW.YOUTUBE.COM/watch?v=x"):
            with self.subTest(link=link):
                self.assertEqual(app.rozpoznaj_zrodlo(link), "youtube")

    def test_spotify(self):
        for link in ("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC?si=abc",
                     "https://open.spotify.com/intl-pl/album/00hXe7ttZI4gjjWYqKAdMX",
                     "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
                     "https://play.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"):
            with self.subTest(link=link):
                self.assertEqual(app.rozpoznaj_zrodlo(link), "spotify")

    def test_obce_i_podstepne(self):
        for tekst in ("", "   ", "dawid podsiadło",
                      "-rf", "--exec", "-o%(title)s",                      # tekst zaczynający się od „-”
                      "https://evil.example/youtube.com/watch?v=x",       # youtube.com tylko w ścieżce
                      "https://youtube.com.evil.example/watch?v=x",       # host, którego podciągiem jest youtube.com
                      "https://notyoutube.com/watch?v=x",
                      "https://evil.example/?u=https://youtube.com",
                      "https://youtube.com@evil.example/watch?v=x",       # dane użytkownika udające hosta
                      "ftp://youtube.com/x", "file:///C:/youtube.com", "javascript:alert(1)",
                      "https://[zle"):                                    # urlsplit rzuca ValueError
            with self.subTest(tekst=tekst):
                self.assertIsNone(app.rozpoznaj_zrodlo(tekst))


class PlaylistaYt(unittest.TestCase):
    def test_playlista(self):
        self.assertTrue(app.to_playlista_yt("https://www.youtube.com/playlist?list=PLabc"))
        self.assertTrue(app.to_playlista_yt("https://music.youtube.com/playlist?list=OLAK5uy_abc"))
        self.assertTrue(app.to_playlista_yt("https://music.youtube.com/browse/MPREb_abc"))

    def test_film_z_miksem_to_jeden_utwor(self):
        self.assertFalse(app.to_playlista_yt("https://www.youtube.com/watch?v=x&list=RDx"))
        self.assertFalse(app.to_playlista_yt("https://youtu.be/x?list=PLabc"))


class ZbudujKomende(unittest.TestCase):
    FOLDER = Path("C:/Users/Ty/Music/Pobrane")

    def test_mp3_jeden_utwor(self):
        link = "https://www.youtube.com/watch?v=x&list=RDx"
        k = app.zbuduj_komende(link, self.FOLDER)
        self.assertEqual(k[-2:], ["--", link])             # „--” = wklejony tekst nigdy nie będzie opcją
        self.assertIn("--ignore-config", k)
        self.assertIn("--no-playlist", k)                   # &list= z miksu = jeden utwór
        self.assertIn("-x", k)
        self.assertEqual(k[k.index("--audio-format") + 1], "mp3")
        self.assertEqual(k[k.index("-P") + 1], str(self.FOLDER))
        self.assertNotIn("--merge-output-format", k)

    def test_playlista_do_podfolderu(self):
        k = app.zbuduj_komende("https://music.youtube.com/playlist?list=OLAK5uy_abc", self.FOLDER)
        self.assertNotIn("--no-playlist", k)
        szablon = k[k.index("-o") + 1]
        self.assertTrue(szablon.startswith("%(playlist_title)s/"), szablon)
        self.assertIn("%(playlist_index)02d", szablon)

    def test_wideo(self):
        link = "https://www.youtube.com/watch?v=x"
        for jakosc in app.JAKOSCI_WIDEO:
            with self.subTest(jakosc=jakosc):
                k = app.zbuduj_komende(link, self.FOLDER, jakosc)
                self.assertEqual(k[k.index("-f") + 1], "bv*+ba/b")
                self.assertEqual(k[k.index("-S") + 1], app.JAKOSCI_WIDEO[jakosc])
                self.assertEqual(k[k.index("--merge-output-format") + 1], "mp4")
                self.assertNotIn("-x", k)
                self.assertNotIn("--embed-thumbnail", k)    # w mp4 okładka byłaby drugą ścieżką obrazu
                self.assertEqual(k[-2:], ["--", link])

    def test_jakosci_spojne(self):
        self.assertEqual(set(app.JAKOSCI_WIDEO), set(app.NAZWY_JAKOSCI))
        self.assertIn(app.DOMYSLNA_JAKOSC, app.JAKOSCI_WIDEO)
        self.assertEqual(app.JAKOSCI_WIDEO["1080p"].split(",")[0], "res:1080")
        with self.assertRaises(KeyError):
            app.zbuduj_komende("https://youtu.be/x", self.FOLDER, "8k")

    def test_odrzuca_nie_youtube(self):
        for tekst in ("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC", "-rf", "", "https://evil.example/x"):
            with self.subTest(tekst=tekst):
                with self.assertRaises(ValueError):
                    app.zbuduj_komende(tekst, self.FOLDER)

    def test_znaczniki_dla_gui(self):
        k = app.zbuduj_komende("https://youtu.be/x", self.FOLDER)
        self.assertIn("download:POSTEP %(progress._percent_str)s", k)
        self.assertTrue(any(x.startswith("before_dl:UTWOR ") for x in k))
        self.assertTrue(any(x.startswith("after_move:PLIK ") for x in k))


class KomendaUtworu(unittest.TestCase):
    def test_sciezka_i_procent(self):
        plik = Path("C:/Users/Ty/Music/Pobrane/Album/01 - 100% Artysta - Tytuł.mp3")
        k = app.komenda_utworu("abc123XYZ-_", plik)
        self.assertEqual(k[-2:], ["--", "https://music.youtube.com/watch?v=abc123XYZ-_"])
        szablon = k[k.index("-o") + 1]
        self.assertTrue(szablon.endswith(".%(ext)s"), szablon)
        self.assertIn("100%% Artysta", szablon)             # % w tytule to nie pole szablonu yt-dlp
        self.assertEqual(szablon.count("%("), 1)
        self.assertIn("--ignore-config", k)
        self.assertIn("--no-playlist", k)


class ProcentPostepu(unittest.TestCase):
    def test_linie(self):
        self.assertEqual(app.procent_postepu("POSTEP  64.0%"), 64.0)
        self.assertEqual(app.procent_postepu("POSTEP 100%"), 100.0)
        self.assertIsNone(app.procent_postepu("POSTEP"))
        self.assertIsNone(app.procent_postepu("POSTEP  N/A"))
        self.assertIsNone(app.procent_postepu("UTWOR 1/3 Tytuł"))
        self.assertIsNone(app.procent_postepu(""))
