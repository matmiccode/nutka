"""Test okna: przełącznik „Teksty do karaoke” (1.8.0). Użycie: build\\venv\\Scripts\\python testy\\okno\\okno_przelacznik_tekstow.py [pl|en]
Pobiera naprawdę jedną piosenkę z YouTube (dwa razy) do folderu tymczasowego - potrzebna sieć, ok. 1 min.

Warunki odbioru:
 T1 bez wpisu w ustawieniach przełącznik jest włączony i widać go w trybie Muzyka
 T2 w trybie Wideo przełącznika nie widać (jest lista jakości); po powrocie na Muzykę wraca
 T3 wyłączenie od razu zapisuje "teksty": false w ustawienia.json
 T4 wyłączony: pobrane mp3 nie ma tekstu (USLT/SYLT) ani pliku .lrc, w logu brak „📝”
 T5 włączony: pobrane mp3 ma tekst (USLT) - jak w 1.7.0
 T6 program uruchomiony z "teksty": false startuje z wyłączonym przełącznikiem
"""

import shutil
import sys
import tempfile
from pathlib import Path

from wspolne import WYNIKI, Sprawdzenia, przygotuj, ustawienia_testowe, zrzut

JEZYK = sys.argv[1] if len(sys.argv) > 1 else "pl"
TMP = Path(tempfile.mkdtemp(prefix="nutka-teksty-"))
POBRANE = TMP / "Pobrane"
app = przygotuj(JEZYK, {"folder": str(POBRANE), "folder_wideo": str(TMP / "Filmy")})
from mutagen.id3 import ID3  # noqa: E402

LINK = "https://music.youtube.com/watch?v=RoYljneBu3s"  # Dawid Podsiadło – Małomiasteczkowy (LRCLIB ma tekst)
sprawdz = Sprawdzenia()
a = app.Aplikacja()
a.geometry("960x720+40+40")


def przelacznik():
    return a.ramka_tekstow.winfo_children()[0]


def log() -> str:
    return a.log.get("1.0", "end")


def plik_mp3():
    pliki = list(POBRANE.rglob("*.mp3"))
    return pliki[0] if pliki else None


def pobierz(potem):
    a.pole_szukaj.delete(0, "end")
    a.pole_szukaj.insert(0, LINK)
    a.pobierz()  # wyłącza „Pobierz” od razu; włącza go obsługa „koniec” po wszystkim (też po tekście)

    def czekaj(n=0):
        if a.przycisk_pobierz.cget("state") == "normal" and a.proces is None:
            a.after(300, lambda: potem(log()))
        elif n > 240:
            print("BŁĄD pobieranie trwa ponad 2 minuty")
            a._zamknij()
        else:
            a.after(500, czekaj, n + 1)
    a.after(1000, czekaj)


def krok1():
    a.update_idletasks()
    sprawdz("T1 domyślnie włączony", a.z_tekstami.get() is True)
    sprawdz("T1 widać w trybie Muzyka", a.ramka_tekstow.winfo_ismapped() and not a.wybor_jakosci.winfo_ismapped())
    zrzut(a, WYNIKI / f"przelacznik-tekstow-{JEZYK}.png")
    a.tryb.set(app.TRYB_WIDEO)
    a._zmien_tryb()
    a.after(400, krok2)


def krok2():
    sprawdz("T2 w trybie Wideo ukryty, jest jakość",
            not a.ramka_tekstow.winfo_ismapped() and a.wybor_jakosci.winfo_ismapped())
    a.tryb.set(app.TRYB_MUZYKA)
    a._zmien_tryb()
    a.after(400, krok3)


def krok3():
    sprawdz("T2 po powrocie na Muzykę wraca", a.ramka_tekstow.winfo_ismapped())
    przelacznik().toggle()  # jak kliknięcie myszą: zmienia zmienną i woła command
    sprawdz("T3 wyłączenie zapisane", ustawienia_testowe().get("teksty") is False)
    pobierz(krok4)


def krok4(tekst):
    plik = plik_mp3()
    sprawdz("T4 mp3 pobrane", plik is not None)
    if plik:
        tagi = ID3(plik)
        sprawdz("T4 bez tekstu w mp3", not tagi.getall("USLT") and not tagi.getall("SYLT"))
        sprawdz("T4 bez pliku .lrc", not plik.with_suffix(".lrc").exists())
        sprawdz("T4 w logu brak 📝", "📝" not in tekst)
        plik.unlink()
    przelacznik().toggle()
    sprawdz("T5 włączenie zapisane", ustawienia_testowe().get("teksty") is True)
    pobierz(krok5)


def krok5(tekst):
    plik = plik_mp3()
    sprawdz("T5 mp3 pobrane", plik is not None)
    if plik:
        tagi = ID3(plik)
        sprawdz("T5 tekst w mp3", bool(tagi.getall("USLT")),
                f"SYLT={len(tagi.getall('SYLT'))} .lrc={plik.with_suffix('.lrc').exists()}")
        sprawdz("T5 w logu 📝", "📝" in tekst)
    przelacznik().toggle()  # T6: zapisane „wyłączone” i nowe uruchomienie
    a._zamknij()


a.after(2500, krok1)
a.mainloop()

b = app.Aplikacja()
b.update_idletasks()
sprawdz("T6 po ponownym starcie wyłączony", b.z_tekstami.get() is False)
b.destroy()
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(sprawdz.koniec())
