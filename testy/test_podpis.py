"""Podpis wydań i aktualizacja programu (aktualizacja_programu.py).

Prawdziwy wektor: plik podpisu wydania 1.5.0 musi przechodzić kluczem publicznym wkompilowanym w program
(zmiana KLUCZ_PUBLICZNY = zainstalowane Nutki nie przyjmą żadnego wydania). Reszta na kluczu testowym
i plikach lokalnych (NUTKA_TEST_WYDANIE) - bez sieci."""

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import aktualizacja_programu as ap

# Nutka-Setup.podpis.json z wydania v1.5.0 (github.com/matmiccode/nutka/releases/tag/v1.5.0)
PODPIS_1_5_0 = {
    "format": 1,
    "plik": "Nutka-Setup.exe",
    "wersja": "1.5.0",
    "sha256": "dde8dae3e95d7baabdb8b62beabe06e3cd11f08918b00c3a66d4faaa69167e2c",
    "podpis": "b2ee983058554e8428637a0819760585407e838596238ca198bfc7f6219300d0"
              "71b347110295c463a212669d3a9481266378243412ce29325169259d1cc8ac0a",
}


def klucz_testowy():
    klucz = Ed25519PrivateKey.generate()
    publiczny = klucz.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return klucz, publiczny


def podpisz(klucz, wersja: str, sha: str, plik: str = ap.NAZWA_INSTALATORA) -> dict:
    """To samo, co robi podpis_wydania.py podpisz."""
    return {"format": ap.FORMAT_PODPISU, "plik": plik, "wersja": wersja, "sha256": sha,
            "podpis": klucz.sign(ap.wiadomosc_podpisu(plik, wersja, sha)).hex()}


class PrawdziwyWektor(unittest.TestCase):
    def test_wydanie_1_5_0_przechodzi_kluczem_z_programu(self):
        self.assertEqual(ap.sprawdz_podpis(PODPIS_1_5_0, "1.5.0"), PODPIS_1_5_0["sha256"])

    def test_suma_wielkimi_literami_tez(self):
        self.assertEqual(ap.sprawdz_podpis(dict(PODPIS_1_5_0, sha256=PODPIS_1_5_0["sha256"].upper()), "1.5.0"),
                         PODPIS_1_5_0["sha256"])

    def test_odrzuca_zmiany(self):
        sha, podpis = PODPIS_1_5_0["sha256"], PODPIS_1_5_0["podpis"]
        for opis, dane, wersja in (
                ("inna wersja (stare wydanie nie uda nowszego)", PODPIS_1_5_0, "1.5.1"),
                ("inny plik", dict(PODPIS_1_5_0, plik="Nutka.exe"), "1.5.0"),
                ("zmieniona suma", dict(PODPIS_1_5_0, sha256=sha[:-1] + ("0" if sha[-1] != "0" else "1")), "1.5.0"),
                ("zmieniony podpis", dict(PODPIS_1_5_0, podpis=podpis[:-1] + ("0" if podpis[-1] != "0" else "1")), "1.5.0"),
                ("suma w złym formacie", dict(PODPIS_1_5_0, sha256="abc"), "1.5.0"),
                ("podpis nie-hex", dict(PODPIS_1_5_0, podpis="zz"), "1.5.0"),
                ("bez podpisu", {k: v for k, v in PODPIS_1_5_0.items() if k != "podpis"}, "1.5.0"),
                ("pusty słownik", {}, "1.5.0")):
            with self.subTest(opis):
                with self.assertRaises(ValueError):
                    ap.sprawdz_podpis(dane, wersja)


class KluczTestowy(unittest.TestCase):
    def setUp(self):
        self.klucz, publiczny = klucz_testowy()
        patch = mock.patch.object(ap, "KLUCZ_PUBLICZNY", publiczny)
        patch.start()
        self.addCleanup(patch.stop)

    def test_wlasny_podpis(self):
        sha = "ab" * 32
        self.assertEqual(ap.sprawdz_podpis(podpisz(self.klucz, "9.9.9", sha), "9.9.9"), sha)

    def test_obcy_klucz_nie_przechodzi(self):
        obcy, _ = klucz_testowy()
        with self.assertRaises(ValueError):
            ap.sprawdz_podpis(podpisz(obcy, "9.9.9", "ab" * 32), "9.9.9")
        with self.assertRaises(ValueError):  # prawdziwy podpis autora też nie - klucz w programie jest inny
            ap.sprawdz_podpis(PODPIS_1_5_0, "1.5.0")

    def test_wiadomosc_wiaze_plik_i_wersje(self):
        self.assertNotEqual(ap.wiadomosc_podpisu("a", "1", "x"), ap.wiadomosc_podpisu("a", "2", "x"))
        self.assertNotEqual(ap.wiadomosc_podpisu("a", "1", "x"), ap.wiadomosc_podpisu("b", "1", "x"))


class Wersje(unittest.TestCase):
    def test_jako_liczby(self):
        self.assertEqual(ap.jako_liczby("v1.5.0"), (1, 5, 0))
        self.assertGreater(ap.jako_liczby("1.10.0"), ap.jako_liczby("1.9.9"))   # liczby, nie napisy
        self.assertGreater(ap.jako_liczby("10.0.0"), ap.jako_liczby("9.9.9"))
        self.assertEqual(ap.jako_liczby(""), ())


class Ustawienia(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nutka-test-ustawienia-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patch = mock.patch.object(ap, "USTAWIENIA", self.tmp / "Nutka" / "ustawienia.json")
        patch.start()
        self.addCleanup(patch.stop)

    def test_zapis_i_odczyt(self):
        self.assertEqual(ap.czytaj_ustawienia(), {})
        ap.zapisz_ustawienie("jezyk", "en")
        ap.zapisz_ustawienia({"folder": "C:\\Muzyka", "jakosc_wideo": "720p"})
        self.assertEqual(ap.czytaj_ustawienia(), {"jezyk": "en", "folder": "C:\\Muzyka", "jakosc_wideo": "720p"})

    def test_zepsuty_plik(self):
        ap.USTAWIENIA.parent.mkdir(parents=True)
        ap.USTAWIENIA.write_text("{to nie json", encoding="utf-8")
        self.assertEqual(ap.czytaj_ustawienia(), {})


class Wydanie(unittest.TestCase):
    """Cały tor aktualizacji na plikach lokalnych (NUTKA_TEST_WYDANIE) z kluczem testowym."""

    def setUp(self):
        self.klucz, publiczny = klucz_testowy()
        self.tmp = Path(tempfile.mkdtemp(prefix="nutka-test-wydanie-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.temp = self.tmp / "temp"  # tu pobierz_instalator() zapisuje instalator (zamiast %TEMP%)
        self.temp.mkdir()
        for patch in (mock.patch.object(ap, "KLUCZ_PUBLICZNY", publiczny),
                      mock.patch.object(ap, "USTAWIENIA", self.tmp / "ustawienia.json"),
                      mock.patch.object(ap.tempfile, "gettempdir", lambda: str(self.temp))):
            patch.start()
            self.addCleanup(patch.stop)
        self.instalator = self.tmp / ap.NAZWA_INSTALATORA
        self.instalator.write_bytes(os.urandom(3 * (1 << 20) + 123))  # > 1 MB = pobieranie w kilku kawałkach
        self.sha = hashlib.sha256(self.instalator.read_bytes()).hexdigest()

    def wydanie(self, wersja="9.9.9", podpis=True, podpisana_suma=None, digest=True, klucz=None,
                url_instalatora=None) -> str:
        """JSON w formacie api.github.com/.../releases/latest z plikami lokalnymi; ustawia NUTKA_TEST_WYDANIE."""
        assets = [{"name": ap.NAZWA_INSTALATORA, "browser_download_url": url_instalatora or str(self.instalator),
                   "size": self.instalator.stat().st_size, **({"digest": f"sha256:{self.sha}"} if digest else {})}]
        if podpis:
            plik_podpisu = self.tmp / ap.NAZWA_PODPISU
            plik_podpisu.write_text(json.dumps(podpisz(klucz or self.klucz, wersja, podpisana_suma or self.sha)),
                                    encoding="utf-8")
            assets.append({"name": ap.NAZWA_PODPISU, "browser_download_url": str(plik_podpisu), "size": 300})
        plik = self.tmp / "wydanie.json"
        plik.write_text(json.dumps({"tag_name": f"v{wersja}", "body": "Co nowego", "assets": assets,
                                    "html_url": f"https://github.com/matmiccode/nutka/releases/tag/v{wersja}"}),
                        encoding="utf-8")
        patch = mock.patch.dict(os.environ, {ap.ZMIENNA_TESTU: str(plik)})
        patch.start()
        self.addCleanup(patch.stop)
        return wersja

    def test_najnowsze_wydanie(self):
        self.wydanie()
        w = ap.najnowsze_wydanie("matmiccode/nutka")
        self.assertEqual((w["wersja"], w["opis"], w["url"], w["sha256"], w["rozmiar"]),
                         ("9.9.9", "Co nowego", str(self.instalator), self.sha, self.instalator.stat().st_size))
        self.assertTrue(w["podpis_url"])
        self.assertTrue(w["strona"].startswith("https://github.com/"))

    def test_bez_digest_i_bez_podpisu(self):
        self.wydanie(podpis=False, digest=False)
        w = ap.najnowsze_wydanie("matmiccode/nutka")
        self.assertIsNone(w["sha256"])
        self.assertIsNone(w["podpis_url"])

    def test_obcy_adres_instalatora(self):
        for adres in ("https://evil.example/Nutka-Setup.exe",
                      "https://github.com/ktos-inny/nutka/releases/download/v9/Nutka-Setup.exe",
                      "http://github.com/matmiccode/nutka/releases/download/v9/Nutka-Setup.exe",
                      str(self.tmp / "nie-ma-takiego-pliku.exe")):
            with self.subTest(adres=adres):
                self.wydanie(url_instalatora=adres)
                with self.assertRaises(ValueError):
                    ap.najnowsze_wydanie("matmiccode/nutka")

    def test_do_zaproponowania(self):
        self.wydanie("9.9.9")
        self.assertEqual(ap.do_zaproponowania("matmiccode/nutka", "1.5.0")["wersja"], "9.9.9")
        self.assertIsNone(ap.do_zaproponowania("matmiccode/nutka", "9.9.9"))
        self.assertIsNone(ap.do_zaproponowania("matmiccode/nutka", "10.0.0"))

    def test_pominieta_wersja(self):
        self.wydanie("9.9.9")
        ap.zapisz_ustawienie("pominieta_wersja", "9.9.9")
        self.assertIsNone(ap.do_zaproponowania("matmiccode/nutka", "1.5.0"))
        self.assertIsNotNone(ap.do_zaproponowania("matmiccode/nutka", "1.5.0", recznie=True))

    def test_bez_podpisu_nie_proponuje(self):
        self.wydanie(podpis=False)
        with self.assertRaises(ValueError):
            ap.do_zaproponowania("matmiccode/nutka", "1.5.0")

    def test_pobierz_instalator(self):
        self.wydanie()
        postepy = []
        plik = ap.pobierz_instalator(ap.najnowsze_wydanie("matmiccode/nutka"), postepy.append)
        self.assertEqual(plik, self.temp / "Nutka-Setup-9.9.9.exe")
        self.assertEqual(hashlib.sha256(plik.read_bytes()).hexdigest(), self.sha)
        self.assertEqual(postepy[-1], 100.0)
        self.assertEqual(postepy, sorted(postepy))
        self.assertEqual([p.name for p in self.temp.iterdir()], ["Nutka-Setup-9.9.9.exe"])  # bez .part

    def test_podmieniony_instalator(self):
        """Podpis (i digest) mówią o innym pliku niż ten, który przyszedł - nic nie zostaje jako .exe."""
        self.wydanie(podpisana_suma="00" * 32, digest=False)
        with self.assertRaises(ValueError):
            ap.pobierz_instalator(ap.najnowsze_wydanie("matmiccode/nutka"))
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_digest_github_niezgodny_z_podpisem(self):
        """Konto GitHub przejęte, podpisu autora nie da się podrobić - różnica = nie pobieramy nawet instalatora."""
        self.wydanie(podpisana_suma="00" * 32)
        with self.assertRaises(ValueError):
            ap.pobierz_instalator(ap.najnowsze_wydanie("matmiccode/nutka"))
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_podpis_obcym_kluczem(self):
        obcy, _ = klucz_testowy()
        self.wydanie(klucz=obcy)
        with self.assertRaises(ValueError):
            ap.pobierz_instalator(ap.najnowsze_wydanie("matmiccode/nutka"))
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_lokalne_pliki_tylko_w_tescie(self):
        """Bez NUTKA_TEST_WYDANIE ścieżka na dysku nie jest dopuszczalnym adresem pliku wydania."""
        self.wydanie()
        dane = json.loads((self.tmp / "wydanie.json").read_text(encoding="utf-8"))
        with mock.patch.dict(os.environ, {ap.ZMIENNA_TESTU: ""}), \
                mock.patch.object(ap, "_pobierz_json", lambda adres: dane):
            with self.assertRaises(ValueError):
                ap.najnowsze_wydanie("matmiccode/nutka")
