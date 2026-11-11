"""Test okna: „?” przy „Teksty do karaoke” (1.8.0). Użycie: build\\venv\\Scripts\\python testy\\okno\\okno_pomoc_tekstow.py [pl|en]
Bez sieci, kilka sekund.

Warunki odbioru:
 T1 „?” stoi obok przełącznika (widoczny w trybie Muzyka)
 T2 klik otwiera okienko z tytułem i treścią w języku programu
 T3 drugi klik nie otwiera drugiego okna
 T4 cała treść mieści się w oknie
"""

import sys

from wspolne import WYNIKI, Sprawdzenia, przygotuj, zrzut

JEZYK = sys.argv[1] if len(sys.argv) > 1 else "pl"
app = przygotuj(JEZYK)
import customtkinter as ctk  # noqa: E402

sprawdz = Sprawdzenia()
a = app.Aplikacja()
a.geometry("960x720+40+40")


def krok1():
    a.update_idletasks()
    pytajnik = next((d for d in a.ramka_tekstow.winfo_children()
                     if isinstance(d, ctk.CTkButton) and d.cget("text") == "?"), None)
    sprawdz("T1 „?” obok przełącznika", pytajnik is not None and pytajnik.winfo_ismapped())
    pytajnik.invoke()
    a.after(800, lambda: krok2(pytajnik))


def krok2(pytajnik):
    okno = a.okno_pomocy_tekstow
    sprawdz("T2 okienko otwarte", okno is not None and okno.winfo_exists())
    napisy = [w.cget("text") for w in okno.winfo_children() if isinstance(w, ctk.CTkLabel)]
    oczekiwany = "Lyrics for karaoke" if JEZYK == "en" else "Teksty do karaoke"
    sprawdz("T2 tytuł i treść", okno.title() == oczekiwany and len(napisy) >= 6, f"{len(napisy)} napisów")
    if JEZYK == "en":
        sprawdz("T2 treść po angielsku", all("ł" not in n and "ą" not in n for n in napisy))
    pytajnik.invoke()
    a.after(500, lambda: krok3(okno))


def krok3(okno):
    okna = [w for w in a.winfo_children() if isinstance(w, ctk.CTkToplevel) and w.winfo_exists()]
    sprawdz("T3 jedno okno po drugim kliku", len(okna) == 1 and a.okno_pomocy_tekstow is okno, f"{len(okna)} okien")
    okno.update_idletasks()
    ostatni = [w for w in okno.winfo_children() if isinstance(w, ctk.CTkLabel)][-1]
    dol = ostatni.winfo_y() + ostatni.winfo_height()
    sprawdz("T4 treść mieści się w oknie", dol <= okno.winfo_height() - 8, f"dół treści {dol}, okno {okno.winfo_height()}")
    zrzut(okno, WYNIKI / f"pomoc-tekstow-{JEZYK}.png")
    a._zamknij()


a.after(2500, krok1)
a.mainloop()
sys.exit(sprawdz.koniec())
