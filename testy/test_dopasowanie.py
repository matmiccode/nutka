"""Dopasowanie utworu ze Spotify w YouTube Music (spotify_lista.py) bez sieci: normalizacja, ocena, wybór."""

import unittest

import spotify_lista as sl


def utwor(tytul="Małomiasteczkowy", wykonawcy=("Dawid Podsiadło",), sekundy=236):
    return sl.Utwor(tytul=tytul, wykonawcy=list(wykonawcy), album="Małomiasteczkowy", sekundy=sekundy,
                    spotify_id="x" * 22)


def wynik(video_id="abc", tytul="Małomiasteczkowy", artysci=("Dawid Podsiadło",), sekundy=236):
    """Wynik klient.search() z ytmusicapi (tylko pola, których używa _ocena)."""
    return {"videoId": video_id, "title": tytul, "artists": [{"name": a} for a in artysci],
            "duration_seconds": sekundy}


class Normalizacja(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(sl._norm("Małomiasteczkowy (feat. Ktoś)"), "malomiasteczkowy")
        self.assertEqual(sl._norm("Trójkąty i Kwadraty [Live]"), "trojkaty i kwadraty")
        self.assertEqual(sl._norm("Song - Remastered 2011"), "song")
        self.assertEqual(sl._norm("Song - 2011 Remaster"), "song")
        self.assertEqual(sl._norm("Tytuł ft. Gość"), "tytul")
        self.assertEqual(sl._norm("  Wielkie   LITERY!!! "), "wielkie litery")
        self.assertEqual(sl._norm("Soft Cell - Tainted Love"), "soft cell tainted love")  # „ft” w środku słowa zostaje

    def test_podobienstwo(self):
        self.assertEqual(sl._podobienstwo("Małomiasteczkowy", "malomiasteczkowy (Official Video)"), 1.0)
        self.assertEqual(sl._podobienstwo("Trójkąty i kwadraty", "Trojkaty i Kwadraty - Live"), 1.0)
        self.assertEqual(sl._podobienstwo("", "x"), 0.0)
        self.assertLess(sl._podobienstwo("Małomiasteczkowy", "Trójkąty i kwadraty"), 0.5)


class Ocena(unittest.TestCase):
    def test_dokladne_trafienie(self):
        self.assertAlmostEqual(sl._ocena(utwor(), wynik(), 7), 4.0)  # tytuł 1.0 × 2 + wykonawca 1.0 + długość 1.0

    def test_odrzuca(self):
        u = utwor()
        for opis, w in (("bez videoId", wynik(video_id="")),
                        ("inna długość = inna wersja", wynik(sekundy=236 + 8)),
                        ("za długi film nawet z większą tolerancją", wynik(sekundy=236 - 20)),
                        ("inny tytuł", wynik(tytul="Trójkąty i kwadraty")),
                        ("inny wykonawca", wynik(artysci=("Kwiat Jabłoni",))),
                        ("niepełny wynik", {"title": "Małomiasteczkowy"})):
            with self.subTest(opis):
                self.assertEqual(sl._ocena(u, w, 15 if "tolerancj" in opis else 7), 0.0)

    def test_blizsza_dlugosc_wygrywa(self):
        u = utwor()
        self.assertGreater(sl._ocena(u, wynik(sekundy=236), 7), sl._ocena(u, wynik(sekundy=241), 7))
        self.assertGreater(sl._ocena(u, wynik(sekundy=241), 7), 0.0)

    def test_dopisek_w_tytule_nie_przeszkadza(self):
        self.assertGreater(sl._ocena(utwor(), wynik(tytul="Małomiasteczkowy (Official Video)"), 7), 3.5)

    def test_wystarczy_jeden_z_wykonawcow(self):
        u = utwor(wykonawcy=("Kwiat Jabłoni", "Dawid Podsiadło"))
        self.assertGreater(sl._ocena(u, wynik(artysci=("Dawid Podsiadło",)), 7), 0.0)


class FikcyjnyKlient:
    """Udaje ytmusicapi.YTMusic: search(zapytanie, filter=..., limit=...) -> lista wyników wg filtra."""

    def __init__(self, songs=(), videos=()):
        self.wyniki = {"songs": list(songs), "videos": list(videos)}
        self.zapytania = []

    def search(self, zapytanie, filter, limit):
        self.zapytania.append((zapytanie, filter))
        return self.wyniki[filter]


class Dopasuj(unittest.TestCase):
    def test_najpierw_oficjalne_utwory(self):
        klient = FikcyjnyKlient(songs=[wynik("zle", sekundy=300), wynik("dobre")], videos=[wynik("film")])
        u = utwor()
        self.assertEqual(sl.dopasuj(u, klient), "dobre")
        self.assertEqual(u.youtube_id, "dobre")
        self.assertEqual(klient.zapytania, [("Dawid Podsiadło Małomiasteczkowy", "songs")])  # filmów nie pytał

    def test_potem_filmy_z_wieksza_tolerancja(self):
        klient = FikcyjnyKlient(songs=[wynik("zle", sekundy=300)], videos=[wynik("film", sekundy=236 + 12)])
        self.assertEqual(sl.dopasuj(utwor(), klient), "film")
        self.assertEqual([f for _, f in klient.zapytania], ["songs", "videos"])

    def test_nic_pewnego(self):
        klient = FikcyjnyKlient(songs=[wynik("a", tytul="Inny utwór")], videos=[wynik("b", sekundy=100)])
        u = utwor()
        self.assertIsNone(sl.dopasuj(u, klient))
        self.assertEqual(u.youtube_id, "")

    def test_puste_wyniki(self):
        self.assertIsNone(sl.dopasuj(utwor(), FikcyjnyKlient()))
