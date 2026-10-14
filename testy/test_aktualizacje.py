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
    def test_nightly_nowsze_od_stabilnego(self):
        self.assertGreater(ak._jako_liczby("2026.10.10.233141.dev0"), ak._jako_liczby("2026.10.7"))
        self.assertGreater(ak._jako_liczby("1.12.3"), ak._jako_liczby("1.9.9"))
        self.assertEqual(ak._jako_liczby("1.12.3"), (1, 12, 3))
        self.assertEqual(ak._jako_liczby("0"), (0,))

    def test_wersja_nieznanego_pakietu(self):
        self.assertEqual(ak.wersja("pakiet-ktorego-na-pewno-nie-ma"), "0")


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
