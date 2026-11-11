"""Test okna: karaoke przy odsłuchu (1.8.0). Użycie: build\\venv\\Scripts\\python testy\\okno\\okno_karaoke.py [pl|en]
Prawdziwy odsłuch z YouTube i tekst z LRCLIB (sieć, ok. 1 min); ffplay dostaje -volume 0 - nic nie gra na głos.

Warunki odbioru:
 T0 odsłuch gra (świeży adres YouTube daje 403 przez ~3 s - 1.7.0 przez to milczała)
 T1 przed odsłuchem nie ma przycisku „Karaoke”, w trakcie jest, po Stop znika
 T2 bez otwartego okna „Karaoke” nic nie idzie do LRCLIB
 T3 okno: tytuł i wykonawca grającego utworu, tekst z czasami
 T4 sekunda z ffplay rośnie razem z czasem
 T5 po pierwszych linijkach podświetlona jest ta, której czas minął, i jest widoczna w oknie
 T6 drugie otwarcie okna bierze tekst z pamięci (bez drugiego zapytania)
 T7 Stop: okno zostaje, podświetlenie stoi
"""

import subprocess
import sys
import time

from wspolne import WYNIKI, Sprawdzenia, przygotuj, zrzut

JEZYK = sys.argv[1] if len(sys.argv) > 1 else "pl"
app = przygotuj(JEZYK)
import teksty_piosenek  # noqa: E402

_popen = subprocess.Popen


class CichyPopen(_popen):
    """ffplay z -volume 0 (test nie gra na głos); reszta bez zmian."""

    def __init__(self, komenda, *a, **k):
        if komenda and komenda[0] == "ffplay":
            komenda = [komenda[0], "-volume", "0", *komenda[1:]]
        super().__init__(komenda, *a, **k)


app.subprocess.Popen = CichyPopen
zapytania = []
_znajdz = teksty_piosenek.znajdz


def licz_znajdz(*a, **k):
    zapytania.append(a)
    return _znajdz(*a, **k)


teksty_piosenek.znajdz = licz_znajdz
LINK = "https://music.youtube.com/watch?v=RoYljneBu3s"  # Małomiasteczkowy, pierwsza linijka ~17 s
sprawdz = Sprawdzenia()
a = app.Aplikacja()
a.geometry("960x720+40+40")
START = 0.0


def czekaj(warunek, potem, limit=30.0, start=None):
    start = start or time.monotonic()
    if warunek():
        potem()
    elif time.monotonic() - start > limit:
        print(f"BŁĄD czekanie ponad {limit} s")
        potem()
    else:
        a.after(200, czekaj, warunek, potem, limit, start)


def krok1():
    global START
    sprawdz("T1 przed odsłuchem brak „Karaoke”", not a.przycisk_karaoke.winfo_ismapped())
    a.pole_szukaj.delete(0, "end")
    a.pole_szukaj.insert(0, LINK)
    START = time.monotonic()
    a.odsluchaj()
    czekaj(lambda: a._karaoke_pozycja is not None and a._karaoke_pozycja[1] > 0.05, krok2)


def krok2():
    a.update_idletasks()
    sprawdz("T0 muzyka rusza do 12 s od kliknięcia", a._karaoke_pozycja and time.monotonic() - START < 12,
            f"{time.monotonic() - START:.1f} s")
    sprawdz("T1 w trakcie jest „Karaoke”", a.przycisk_karaoke.winfo_ismapped())
    if not a._karaoke_pozycja:
        a._zamknij()
        return
    a.after(2000, krok3)


def krok3():
    sprawdz("T2 bez okna nic nie idzie do LRCLIB", not zapytania, f"{len(zapytania)} zapytań")
    p1 = a._karaoke_pozycja[1]
    a.after(2000, lambda: krok4(p1))


def krok4(p1):
    p2 = a._karaoke_pozycja[1]
    sprawdz("T4 sekunda z ffplay rośnie", 1.5 <= p2 - p1 <= 2.6, f"{p1:.2f} -> {p2:.2f}")
    a.przycisk_karaoke.invoke()
    czekaj(lambda: bool(a._karaoke_czasy), krok5)


def krok5():
    a.update_idletasks()
    sprawdz("T3 tytuł i wykonawca", (a._k_tytul.cget("text"), a._k_wykonawca.cget("text"))
            == ("Małomiasteczkowy", "Dawid Podsiadło"), f"{a._k_tytul.cget('text')} / {a._k_wykonawca.cget('text')}")
    sprawdz("T3 tekst z czasami", len(a._karaoke_czasy) > 10 and len(zapytania) == 1,
            f"{len(a._karaoke_czasy)} linijek, {len(zapytania)} zapytań")
    czekaj(lambda: a._karaoke_biezaca >= 2, krok6, limit=40)


def krok6():
    a.update_idletasks()
    sekunda = a._karaoke_pozycja[1]
    oczekiwana = teksty_piosenek.indeks_linii(a._karaoke_czasy, int(sekunda * 1000))
    podswietlone = a._k_tekst.tag_ranges("biezaca")
    tekst = a._k_tekst.get(*podswietlone) if podswietlone else ""
    sprawdz("T5 podświetlona właściwa linijka", abs(a._karaoke_biezaca - oczekiwana) <= 1 and tekst,
            f"{sekunda:.1f} s, linijka {a._karaoke_biezaca} „{tekst}”")
    sprawdz("T5 linijka widoczna w oknie", a._k_tekst.dlineinfo(f"{a._karaoke_biezaca + 1}.0") is not None)
    zrzut(a.okno_karaoke, WYNIKI / f"karaoke-{JEZYK}.png")  # prawdziwy tekst - tylko lokalnie, nie do docs
    a.okno_karaoke.destroy()
    a.after(500, krok7)


def krok7():
    a.przycisk_karaoke.invoke()
    a.after(800, krok8)


def krok8():
    sprawdz("T6 drugie otwarcie z pamięci", len(zapytania) == 1 and bool(a._karaoke_czasy), f"{len(zapytania)} zapytań")
    a.odsluchaj()  # „■ Stop”
    a.after(1500, krok9)


def krok9():
    a.update_idletasks()
    sprawdz("T1 po Stop brak „Karaoke”", not a.przycisk_karaoke.winfo_ismapped())
    przed = a._karaoke_biezaca
    a.after(3000, lambda: krok10(przed))


def krok10(przed):
    sprawdz("T7 okno zostaje, podświetlenie stoi", a._karaoke_otwarte() and a._karaoke_biezaca == przed)
    a._zamknij()


a.after(2500, krok1)
a.mainloop()
sys.exit(sprawdz.koniec())
