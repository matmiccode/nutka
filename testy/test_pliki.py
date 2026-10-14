"""Nazwy plików z internetu (spotify_lista.py): znaki zabronione, nazwy urządzeń, ścieżka zawsze w folderze."""

import tempfile
import unittest
from pathlib import Path

import spotify_lista as sl
import teksty


def utwor(tytul="Małomiasteczkowy", wykonawcy=("Dawid Podsiadło",), numer=0):
    return sl.Utwor(tytul=tytul, wykonawcy=list(wykonawcy), album="Małomiasteczkowy", sekundy=236,
                    spotify_id="x" * 22, numer=numer)


class Rozpoznaj(unittest.TestCase):
    ID = "4uLU6hMCjMI75M1A2tKUQC"

    def test_linki(self):
        self.assertEqual(sl.rozpoznaj(f"https://open.spotify.com/track/{self.ID}?si=abc"), ("track", self.ID))
        self.assertEqual(sl.rozpoznaj(f"https://open.spotify.com/intl-pl/album/{self.ID}"), ("album", self.ID))
        self.assertEqual(sl.rozpoznaj(f"spotify:playlist:{self.ID}"), ("playlist", self.ID))

    def test_nie_linki(self):
        for tekst in (f"https://open.spotify.com/artist/{self.ID}", "https://open.spotify.com/track/krotkie",
                      "spotify:", "", "https://open.spotify.com/"):
            with self.subTest(tekst=tekst):
                self.assertIsNone(sl.rozpoznaj(tekst))


class BezpiecznaNazwa(unittest.TestCase):
    def test_znaki_zabronione(self):
        self.assertEqual(sl.bezpieczna_nazwa('AC/DC: "Back" <in> Black?*|\\'), "ACDC Back in Black")

    def test_znaki_sterujace(self):
        self.assertEqual(sl.bezpieczna_nazwa("a\x00b\nc\td"), "abcd")

    def test_kropki_i_spacje_na_koncach(self):
        # Win32 ignoruje kropki i spacje na końcu nazwy, więc „.. ” wskazywałoby katalog nadrzędny
        self.assertEqual(sl.bezpieczna_nazwa("  ..Tytuł.. "), "Tytuł")
        self.assertEqual(sl.bezpieczna_nazwa("..\\..\\Windows"), "Windows")
        self.assertEqual(sl.bezpieczna_nazwa("../../x"), "x")
        for pusty in ("", "   ", "..", " . . "):
            with self.subTest(pusty=pusty):
                self.assertEqual(sl.bezpieczna_nazwa(pusty), "bez nazwy")

    def test_nazwy_urzadzen(self):
        for nazwa in ("CON", "con", "Nul", "COM1", "lpt9", "AUX.mp3", "con.tar.gz", "PRN "):
            with self.subTest(nazwa=nazwa):
                self.assertTrue(sl.bezpieczna_nazwa(nazwa).startswith("_"), nazwa)
        for nazwa in ("CONTROL", "COM10", "Console", "Nullable", "LPT0", "CON - Tytuł"):
            with self.subTest(nazwa=nazwa):
                self.assertEqual(sl.bezpieczna_nazwa(nazwa), nazwa)

    def test_dlugosc(self):
        self.assertEqual(len(sl.bezpieczna_nazwa("a" * 300)), 150)
        # ucięcie do 150 znaków nie może zostawić kropki ani spacji na końcu
        for nazwa in ("a" * 149 + " .", "a" * 149 + ". b", "a" * 148 + " . c"):
            with self.subTest(nazwa=nazwa):
                self.assertFalse(sl.bezpieczna_nazwa(nazwa).endswith((" ", ".")))


class SciezkaPliku(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.gettempdir()) / "nutka-testy-pliki"  # nie musi istnieć - nic nie zapisujemy
        self._jezyk = teksty.jezyk()
        teksty.ustaw("pl")

    def tearDown(self):
        teksty.ustaw(self._jezyk)

    def test_utwor(self):
        lista = sl.Lista("Małomiasteczkowy", "utwór")
        self.assertEqual(sl.sciezka_pliku(utwor(), lista, self.folder),
                         self.folder / "Dawid Podsiadło - Małomiasteczkowy.mp3")

    def test_album_z_numerami(self):
        lista = sl.Lista("Małomiasteczkowy", "album")
        self.assertEqual(sl.sciezka_pliku(utwor(numer=3), lista, self.folder),
                         self.folder / "Małomiasteczkowy" / "03 - Dawid Podsiadło - Małomiasteczkowy.mp3")

    def test_playlista_bez_numerow(self):
        lista = sl.Lista("Moja: playlista?", "playlista")  # kolejność w playliście się zmienia, numer by mylił
        self.assertEqual(sl.sciezka_pliku(utwor(numer=3), lista, self.folder),
                         self.folder / "Moja playlista" / "Dawid Podsiadło - Małomiasteczkowy.mp3")

    def test_bez_wykonawcy(self):
        plik = sl.sciezka_pliku(utwor(wykonawcy=()), sl.Lista("x", "utwór"), self.folder)
        self.assertEqual(plik.name, "Nieznany - Małomiasteczkowy.mp3")

    def test_zawsze_w_folderze(self):
        for tytul, nazwa_listy in (("../../../Windows/evil", "..\\..\\.."), ("..", ".. "),
                                   ("C:\\Windows\\x", "\\\\serwer\\udzial"), ("CON", "NUL")):
            for rodzaj in ("utwór", "album", "playlista"):
                with self.subTest(tytul=tytul, lista=nazwa_listy, rodzaj=rodzaj):
                    plik = sl.sciezka_pliku(utwor(tytul=tytul, wykonawcy=(nazwa_listy,), numer=1),
                                            sl.Lista(nazwa_listy, rodzaj), self.folder)
                    self.assertTrue(plik.resolve().is_relative_to(self.folder.resolve()), plik)
                    self.assertEqual(len(plik.relative_to(self.folder).parts), 1 if rodzaj == "utwór" else 2)
                    self.assertTrue(plik.name.endswith(".mp3"))
