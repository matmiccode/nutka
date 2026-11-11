"""Karaoke przy odsłuchu (od 1.8.0) bez sieci i bez okna.

Warunki odbioru:
- bieżąca sekunda piosenki = zegar audio, który ffplay (-stats) wypisuje na stderr („  12.34 M-A: …”);
  inne linie (puste, błędy) nic nie zmieniają;
- dane utworu do szukania tekstu przychodzą z yt-dlp razem z adresem strumienia: wykonawca (pierwszy z listy,
  przy zwykłym filmie kanał), tytuł utworu, album, długość; brak albumu albo długości nie psuje odczytu;
- podświetlona linijka = ostatnia, której czas już minął; przed pierwszą nic nie jest podświetlone.
"""

import unittest

import app
import teksty_piosenek as tp


class PozycjaFfplay(unittest.TestCase):
    def test_zegar_audio(self):
        self.assertEqual(app.pozycja_ffplay(b"   12.34 M-A:  0.000 fd=   0 aq=    8KB vq=    0KB sq=    0B "), 12.34)
        self.assertEqual(app.pozycja_ffplay(b"  -0.02 M-A: -0.000 fd=   0 aq=    8KB vq=    0KB sq=    0B "), 0.0)
        self.assertEqual(app.pozycja_ffplay(b" 3601.50 A-V:  0.010 fd=   2"), 3601.5)

    def test_inne_linie(self):
        for linia in (b"", b"   ", b"nan    :  0.000 fd=   0", b"[mp3 @ 0000] Estimating duration", b"12.34"):
            self.assertIsNone(app.pozycja_ffplay(linia), linia)


class DaneStrumienia(unittest.TestCase):
    def test_utwor_youtube_music(self):
        wyjscie = "Małomiasteczkowy\nDawid Podsiadło\nMałomiasteczkowy\nMałomiasteczkowy\n203\nhttps://rr6.googlevideo.com/x\n"
        self.assertEqual(app.dane_strumienia(wyjscie),
                         ("Małomiasteczkowy", "https://rr6.googlevideo.com/x",
                          ("Dawid Podsiadło", "Małomiasteczkowy", "Małomiasteczkowy", 203)))

    def test_film_bez_albumu_dlugosc_ulamkowa(self):
        wyjscie = ("Queen – Bohemian Rhapsody (Official Video)\nQueen Official\nQueen – Bohemian Rhapsody (Official Video)"
                   "\n\n358.6\nhttps://rr5.googlevideo.com/y")
        tytul, adres, (kto, co, album, sekundy) = app.dane_strumienia(wyjscie)
        self.assertEqual((kto, album, sekundy), ("Queen Official", "", 359))

    def test_brak_dlugosci_i_bledy(self):
        self.assertEqual(app.dane_strumienia("T\nW\nT\nA\nNA\nhttps://a/b")[2][3], 0)
        self.assertIsNone(app.dane_strumienia(""))
        self.assertIsNone(app.dane_strumienia("ERROR: Video unavailable"))


class IndeksLinii(unittest.TestCase):
    CZASY = [17120, 20500, 24000, 62750]

    def test_przed_pierwsza(self):
        self.assertEqual(tp.indeks_linii(self.CZASY, 0), -1)
        self.assertEqual(tp.indeks_linii(self.CZASY, 17119), -1)
        self.assertEqual(tp.indeks_linii([], 5000), -1)

    def test_biezaca(self):
        self.assertEqual(tp.indeks_linii(self.CZASY, 17120), 0)
        self.assertEqual(tp.indeks_linii(self.CZASY, 23999), 1)
        self.assertEqual(tp.indeks_linii(self.CZASY, 999999), 3)


if __name__ == "__main__":
    unittest.main()
