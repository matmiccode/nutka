"""Pomocnicze funkcje okna (app.py, youtube_lista.py) bez sieci: podgląd jednego filmu jako wiersz tabeli,
adresy do menu prawego klawisza, raport do zgłoszenia bez nazwy konta Windows, adres strony zgłoszenia,
stopka i okno „O programie” (podpis, strona programu, licencje) w obu językach."""

import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import app
import spotify_lista as sl
import teksty
import youtube_lista


class WierszFilmu(unittest.TestCase):
    def test_utwor_youtube_music(self):
        dane = {"title": "Dawid Podsiadło - Małomiasteczkowy (Official Video)", "track": "Małomiasteczkowy",
                "artists": ["Dawid Podsiadło"], "album": "Małomiasteczkowy", "channel": "SonyMusicPoland", "duration": 204}
        w = youtube_lista.wiersz_filmu(dane, "https://youtu.be/x")
        self.assertEqual(w, {"tytul": "Małomiasteczkowy", "wykonawca": "Dawid Podsiadło", "album": "Małomiasteczkowy",
                             "czas": "3:24", "link": "https://youtu.be/x"})  # link = wklejony, nie znormalizowany

    def test_zwykly_film(self):
        dane = {"title": "Me at the zoo", "channel": "jawed - Topic", "uploader": "jawed", "duration": 19}
        w = youtube_lista.wiersz_filmu(dane, "https://www.youtube.com/watch?v=jNQXAC9IVRw")
        self.assertEqual((w["tytul"], w["wykonawca"], w["album"], w["czas"]), ("Me at the zoo", "jawed", "", "0:19"))

    def test_braki(self):
        w = youtube_lista.wiersz_filmu({}, "x")
        self.assertEqual(w, {"tytul": "", "wykonawca": "", "album": "", "czas": "", "link": "x"})


class LinkiUtworu(unittest.TestCase):
    def test_spotify_bez_dopasowania(self):
        u = sl.Utwor("T", ["W"], "A", 100, "4uLU6hMCjMI75M1A2tKUQC")
        self.assertEqual(app.linki_utworu(u), {"youtube": "", "spotify": "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
                                               "plik": None})

    def test_youtube_z_plikiem(self):
        u = sl.Utwor("T", ["W"], "", 100, "", youtube_id="abc-_123")
        istniejacy = Path(__file__)
        self.assertEqual(app.linki_utworu(u, istniejacy), {"youtube": "https://www.youtube.com/watch?v=abc-_123",
                                                           "spotify": "", "plik": istniejacy})
        self.assertIsNone(app.linki_utworu(u, Path("C:/nie/ma/takiego.mp3"))["plik"])


class Zgloszenie(unittest.TestCase):
    def test_bez_nazwy_uzytkownika(self):
        dom = str(Path.home())
        raport = f"pakiety  {dom}\\AppData\\Local\\Nutka\\pakiety -> wbudowane\nffmpeg   {dom.replace(chr(92), '/')}/x/ffmpeg.exe\nOK"
        czysty = app.bez_nazwy_uzytkownika(raport)
        self.assertNotIn(dom, czysty)
        self.assertNotIn(Path.home().name, czysty)
        self.assertIn("~\\AppData\\Local\\Nutka\\pakiety", czysty)
        self.assertIn("~/x/ffmpeg.exe", czysty)

    def test_adres_zgloszenia(self):
        adres = app.adres_zgloszenia("Nutka 1.6.0 - autotest\nWYNIK    NIE DZIAŁA: spotify\n")
        czesci = urlsplit(adres)
        self.assertEqual((czesci.scheme, czesci.netloc, czesci.path), ("https", "github.com", f"/{app.REPO_GITHUB}/issues/new"))
        parametry = parse_qs(czesci.query)
        self.assertEqual(parametry["title"], [f"Nutka {app.WERSJA}: "])
        tresc = parametry["body"][0]
        self.assertIn("```\nNutka 1.6.0 - autotest\nWYNIK    NIE DZIAŁA: spotify\n```", tresc)
        self.assertIn("**", tresc)  # nagłówki do wypełnienia przez użytkownika
        self.assertLess(len(adres), 8000)


class OProgramie(unittest.TestCase):
    """Standard MATCODE: stopka „MATCODE · wersja X”, w „O programie” link do strony programu i „Licencje”."""

    def setUp(self):
        self._jezyk = teksty.jezyk()
        self.addCleanup(teksty.ustaw, self._jezyk)

    def test_podpis_stopki(self):
        teksty.ustaw("pl")
        self.assertEqual(app.podpis_stopki(), f"MATCODE · wersja {app.WERSJA}")
        teksty.ustaw("en")
        self.assertEqual(app.podpis_stopki(), f"MATCODE · version {app.WERSJA}")

    def test_strona_programu(self):
        teksty.ustaw("pl")
        self.assertEqual(app.strona_programu(), "https://matmiccode.github.io/nutka/")
        teksty.ustaw("en")
        self.assertEqual(app.strona_programu(), "https://matmiccode.github.io/nutka/en/")

    def test_licencje_obok_programu(self):
        # zbuduj.ps1 kopiuje LICENSE i THIRD-PARTY.md obok Nutka.exe; w repo leżą w korzeniu
        tresc = app.tekst_licencji(Path(app.__file__).parent)
        self.assertIn("MIT License", tresc)
        self.assertIn("MATCODE", tresc)
        self.assertIn("FFmpeg", tresc)  # składniki z THIRD-PARTY.md
        self.assertIn("https://github.com/quodlibet/mutagen", tresc)
        # w oknie zwykły tekst: tabela z markdownu zamieniona na listę, bez znaczników
        self.assertNotIn("| --- |", tresc)
        self.assertNotIn("`", tresc)
        self.assertNotIn("# ", tresc)

    def test_licencje_brak_plikow(self):
        with tempfile.TemporaryDirectory() as pusty:
            tresc = app.tekst_licencji(Path(pusty))
        self.assertIn(f"https://github.com/{app.REPO_GITHUB}/blob/master/LICENSE", tresc)
        self.assertIn(f"https://github.com/{app.REPO_GITHUB}/blob/master/THIRD-PARTY.md", tresc)


if __name__ == "__main__":
    unittest.main()
