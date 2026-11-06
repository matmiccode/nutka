"""Ciche aktualizacje pakietów (aktualizacje.py) bez sieci: wersje, wymagany yt-dlp-ejs, sys.path, sprzątanie."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aktualizacje as ak


class Wersje(unittest.TestCase):
    def test_wersja_nieznanego_pakietu(self):
        self.assertEqual(ak.wersja("pakiet-ktorego-na-pewno-nie-ma"), "0")

    def test_ten_sam_numer_w_dwoch_zapisach(self):
        # od 2026-10 PyPI podaje nightly yt-dlp jako „….dev0”, a rozpakowany pakiet mówi o sobie „…dev”
        self.assertEqual(ak._klucz_wersji("2026.10.23.233055dev"), ak._klucz_wersji("2026.10.23.233055.dev0"))
        self.assertEqual(ak._klucz_wersji("2026.10.23.233055.dev"), ak._klucz_wersji("2026.10.23.233055dev0"))
        self.assertEqual(ak._klucz_wersji("1.0"), ak._klucz_wersji("1"))

    def test_kolejnosc(self):
        k = ak._klucz_wersji
        self.assertGreater(k("2026.11.4.232659.dev0"), k("2026.10.23.233055dev"))
        self.assertGreater(k("2026.10.10.233141.dev0"), k("2026.10.7"))
        self.assertGreater(k("1.12.3"), k("1.9.9"))
        self.assertGreater(k("1.0.1"), k("1.0"))
        self.assertGreater(k("2026.10.10"), k("2026.10.10.dev0"))  # wydanie stabilne po swoim nightly
        self.assertGreater(k("1.2.8"), k("0"))


class Aktualizuj(unittest.TestCase):
    """Cały tor aktualizuj() bez sieci: PyPI, rozpakowanie i test w procesie podstawione."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nutka-test-akt-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.wersje = {"yt-dlp": "2026.10.10.233141.dev0", "ytmusicapi": "1.12.3", "spotapi": "1.2.8"}
        self.najnowsze = dict(self.wersje, **{"yt-dlp": "2026.11.4.232659.dev0"})
        self.rozpakowane = []
        sciezka = list(sys.path)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), sciezka))  # zastosuj() dopisuje do sys.path

        def rozpakuj(pakiet, wer):
            katalog = self.tmp / f"{pakiet}-{wer}"
            katalog.mkdir()
            self.rozpakowane.append(pakiet)
            return katalog
        for nazwa, atrapa in {"FOLDER": self.tmp, "STAN": self.tmp / "aktywne.json",
                              "_najnowsza": lambda p: self.najnowsze[p], "wersja": lambda p: self.wersje.get(p, "0"),
                              "_rozpakuj_wheel": rozpakuj, "_wymagany_ejs": lambda _k: None}.items():
            patch = mock.patch.object(ak, nazwa, atrapa)
            patch.start()
            self.addCleanup(patch.stop)

    def test_nowy_nightly_w_innym_zapisie_przechodzi(self):
        # kandydat w procesie testowym przedstawia się „…dev” - to ta sama wersja, aktualizacja ma wejść
        wynik_testu = dict(self.wersje, **{"yt-dlp": "2026.11.4.232659dev", "yt-dlp-ejs": "0.8.0"})
        with mock.patch.object(ak, "_sprawdz_w_procesie", return_value=wynik_testu):
            self.assertEqual(ak.aktualizuj(["exe"]), {"yt-dlp": "2026.11.4.232659.dev0"})
        stan = json.loads((self.tmp / "aktywne.json").read_text(encoding="utf-8"))
        self.assertTrue(Path(stan["yt-dlp"]).is_dir())

    def test_zepsuty_kandydat_wycofany(self):
        with mock.patch.object(ak, "_sprawdz_w_procesie", return_value={}):  # import w nowym procesie padł
            with self.assertRaises(RuntimeError):
                ak.aktualizuj(["exe"])
        self.assertFalse((self.tmp / "aktywne.json").exists())
        self.assertFalse((self.tmp / "yt-dlp-2026.11.4.232659.dev0").exists())

    def test_zainstalowana_w_innym_zapisie_to_nie_nowa(self):
        # po udanej aktualizacji pakiet mówi „…dev”, a PyPI dalej „….dev0” - nie pobieramy go co 6 godzin od nowa
        self.wersje["yt-dlp"] = "2026.11.4.232659dev"
        with mock.patch.object(ak, "_sprawdz_w_procesie") as test:
            self.assertEqual(ak.aktualizuj(["exe"]), {})
        test.assert_not_called()
        self.assertEqual(self.rozpakowane, [])


class Tymczasowy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nutka-test-pakiety-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)


class WymaganyEjs(Tymczasowy):
    def test_z_metadata(self):
        meta = self.tmp / "yt_dlp-2026.10.10.233141.dev0.dist-info" / "METADATA"
        meta.parent.mkdir()
        meta.write_text("Metadata-Version: 2.4\nName: yt-dlp\nRequires-Dist: yt-dlp-ejs==0.8.0\n"
                        "Requires-Dist: brotli; extra == 'default'\n", encoding="utf-8")
        self.assertEqual(ak._wymagany_ejs(self.tmp), "0.8.0")

    def test_bez(self):
        self.assertIsNone(ak._wymagany_ejs(self.tmp))


class Zastosuj(Tymczasowy):
    def test_kandydat_z_env(self):
        istnieje, brak = self.tmp / "yt-dlp-1", self.tmp / "nie-ma"
        istnieje.mkdir()
        stan = {"yt-dlp": str(istnieje), "spotapi": str(brak)}
        sciezka = list(sys.path)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), sciezka))
        with mock.patch.dict(os.environ, {ak.ZMIENNA_TESTU: json.dumps(stan)}):
            ak.zastosuj()
            self.assertEqual(sys.path[0], str(istnieje))
            self.assertNotIn(str(brak), sys.path)
            ak.zastosuj()  # drugi raz (drugi proces/okno) nie dubluje wpisu
        self.assertEqual(sys.path.count(str(istnieje)), 1)


class Sprzatanie(Tymczasowy):
    def setUp(self):
        super().setUp()
        patch = mock.patch.object(ak, "FOLDER", self.tmp)
        patch.start()
        self.addCleanup(patch.stop)
        self.uzywany, self.stary, self.plik = self.tmp / "yt-dlp-2", self.tmp / "yt-dlp-1", self.tmp / "aktywne.json"
        self.uzywany.mkdir()
        self.stary.mkdir()
        self.plik.write_text("{}", encoding="utf-8")

    def test_usuwa_nieuzywane_katalogi(self):
        ak._posprzataj({"yt-dlp": str(self.uzywany)})
        self.assertTrue(self.uzywany.is_dir())
        self.assertFalse(self.stary.exists())
        self.assertTrue(self.plik.exists())  # pliki zostają

    def test_swieze_zostaje(self):
        ak._posprzataj({}, starsze_niz_s=3600)  # może je właśnie rozpakowywać drugie okno
        self.assertTrue(self.stary.is_dir())
