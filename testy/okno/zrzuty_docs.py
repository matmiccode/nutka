"""Zrzuty do strony i instrukcji (docs/img, docs/img/en). Użycie z katalogu projektu:
    build\\venv\\Scripts\\python testy\\okno\\zrzuty_docs.py pl|en

Sceny (okno 960x720 jak dotąd, folder C:\\Users\\Ty\\..., ustawienia tymczasowe):
  okno.png       wyniki prawdziwego wyszukiwania „dawid podsiadło”, zaznaczony „Małomiasteczkowy”
  wideo.png      te same wyniki w trybie „Wideo (mp4)”, pobieranie w toku (42 %)
  playlista.png  playlista Spotify w trakcie pobierania - dane PODSTAWIONE (statusy, 1 „masz już”, 1 błąd)
  karaoke.png    okno „Karaoke” z piosenką ludową (PL „Wlazł kotek na płotek”, EN „Twinkle, Twinkle, Little Star”) -
                 na publicznej stronie żadnych prawdziwych tekstów piosenek (prawa autorskie)
Wyszukiwanie idzie do YouTube Music (sieć); reszta bez sieci.
"""

import sys
import time

from wspolne import REPO, przygotuj, zrzut

JEZYK = sys.argv[1] if len(sys.argv) > 1 else "pl"
app = przygotuj(JEZYK)
import spotify_lista  # noqa: E402
import teksty_piosenek  # noqa: E402
from teksty import t  # noqa: E402

CEL = REPO / "docs" / "img" / ("en" if JEZYK == "en" else "")
PLAYLISTA = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
# (tytuł, wykonawcy, album, sekundy, status) - status "" = w kolejce, "masz" = już jest (odznaczony)
UTWORY = [
    ("Patient Zero", ["Taylor Swift"], "The Life of a Showgirl", 226, "✓ pobrano"),
    ("the cure", ["Olivia Rodrigo"], "the cure", 297, "✓ pobrano"),
    ("Nicole Kidman", ["ADÉLA"], "PRIMA", 181, "pobieram 64 %"),
    ("Earrings", ["Malcolm Todd"], "Sweet Boy", 152, "masz"),
    ("BbY WOW", ["KAROL G", "Judeline", "ruso"], "NO ME ARREPIENTO DE ESTE AMOR", 226, "✗ brak na YouTube"),
    ("Loser", ["Tame Impala"], "Deadbeat", 222, "pobieram 12 %"),
    ("Golden", ["HUNTR/X"], "KPop Demon Hunters", 194, "szukam…"),
    ("Ordinary", ["Alex Warren"], "You'll Be Alright, Kid", 186, "w kolejce"),
]
PIOSENKA = {  # (wykonawca, tytuł, linijki co 3 s) - utwory ludowe / domena publiczna
    "pl": ("Piosenka ludowa", "Wlazł kotek na płotek",
           ["Wlazł kotek na płotek", "i mruga,", "ładna to piosenka,", "niedługa.",
            "Niedługa, niekrótka,", "lecz w sam raz,", "zaśpiewaj, koteczku,", "jeszcze raz."]),
    "en": ("Traditional", "Twinkle, Twinkle, Little Star",
           ["Twinkle, twinkle, little star,", "How I wonder what you are!", "Up above the world so high,",
            "Like a diamond in the sky.", "Twinkle, twinkle, little star,", "How I wonder what you are!",
            "When the blazing sun is gone,", "When he nothing shines upon,"]),
}

a = app.Aplikacja()
a.geometry("960x720+40+40")


def wyczysc_log():
    a.log.configure(state="normal")
    a.log.delete("1.0", "end")
    a.log.configure(state="disabled")


def czekaj(warunek, potem, limit=25.0, start=None):
    start = start or time.monotonic()
    if warunek() or time.monotonic() - start > limit:
        potem()
    else:
        a.after(200, czekaj, warunek, potem, limit, start)


def szukaj():
    a.pole_szukaj.insert(0, "dawid podsiadło")
    a.szukaj()
    czekaj(lambda: bool(a.wyniki.get_children()), okno)


def okno():
    wiersz = next((iid for iid, p in a._pelne_teksty.items() if p["tytul"] == "Małomiasteczkowy"), None)
    if wiersz:
        a.wyniki.selection_set(wiersz)
        a.wyniki.see(wiersz)
    a.pole_szukaj.focus()
    a.after(800, lambda: (zrzut(a, CEL / "okno.png"), wideo()))


def wideo():
    a.tryb.set(app.TRYB_WIDEO)
    a._zmien_tryb(zapisz=False)
    a.przycisk_pobierz.configure(state="disabled")
    a._ustaw_postep(42)
    wyczysc_log()
    a._dopisz(t("▶ Start (wideo {jakosc}): {link}").format(
        jakosc="1080p", link="https://music.youtube.com/watch?v=RoYljneBu3s"))
    a._dopisz("♪ Dawid Podsiadło - Małomiasteczkowy")
    a.after(800, lambda: (zrzut(a, CEL / "wideo.png"), playlista()))


def playlista():
    a._schowaj_postep()
    a.tryb.set(app.TRYB_MUZYKA)
    a._zmien_tryb(zapisz=False)
    a.pole_szukaj.delete(0, "end")
    a.pole_szukaj.insert(0, PLAYLISTA)
    lista = spotify_lista.Lista("Today's Top Hits", "playlista", [
        spotify_lista.Utwor(tytul, wykonawcy, album, sekundy, f"x{i}") for i, (tytul, wykonawcy, album, sekundy, _)
        in enumerate(UTWORY)], zrodlo="spotify")
    a._pokaz_liste(PLAYLISTA, lista)
    for (iid, _), (*_, status) in zip(a.wiersze_listy.items(), UTWORY):
        if status == "masz":
            a._ustaw_status(iid, t("masz już"))
            a._ustaw_zaznaczenie(iid, False)
        elif status.startswith(("✓", "✗")):
            znak, slowa = status.split(" ", 1)
            a._ustaw_status(iid, f"{znak} {t(slowa)}")
        elif status.startswith("pobieram"):
            a._ustaw_status(iid, t("pobieram {p} %").format(p=status.split()[1]))
        else:
            a._ustaw_status(iid, t(status))
    a._ustaw_opis_listy(dopisek=f"{len(UTWORY)} {t('utw.')}  ·  {t('{n} już masz').format(n=1)}", postep="3/7")
    a.przycisk_pobierz.configure(state="normal", text=t("Zatrzymaj"))
    a._ustaw_postep(100 * 3 / 7, "3/7")
    wyczysc_log()
    opis = f"{t('Playlista')} {t('„')}Today's Top Hits”  ·  {len(UTWORY)} {t('utw.')}" + \
        t(" – {n} już masz, są odznaczone.").format(n=1)
    a._dopisz(t("♫ {opis} Odznacz, czego nie chcesz, i kliknij „Pobierz zaznaczone”.").format(opis=opis))
    a._dopisz(t("▶ Pobieram {n} utw. z „{nazwa}” (po {k} naraz)…").format(
        n=len(UTWORY) - 1, nazwa="Today's Top Hits", k=app.ROWNOLEGLE_POBIERANIA))
    a.after(1000, lambda: (zrzut(a, CEL / "playlista.png"), karaoke()))


def karaoke():
    kto, tytul, linijki = PIOSENKA[JEZYK]
    lrc = "\n".join(f"[00:{2 + 3 * i:02d}.00] {linia}" for i, linia in enumerate(linijki))
    a._karaoke_utwor = (1, (kto, tytul, "", 3 * len(linijki) + 4))
    a._karaoke_slowa = (1, teksty_piosenek.Slowa("\n".join(linijki), lrc))

    def pozycja():  # „gra” 3. linijka (jakby ffplay podawał 9,5 s)
        a._karaoke_pozycja = (1, 9.5, time.monotonic())
        a.after(50, pozycja)
    pozycja()
    a._pokaz_karaoke()
    a.okno_karaoke.geometry("620x560+80+80")
    a.after(1500, lambda: (zrzut(a.okno_karaoke, CEL / "karaoke.png"), koniec()))


def koniec():
    print("zrzuty:", ", ".join(p.name for p in sorted(CEL.glob("*.png")) if p.stat().st_mtime > START))
    a._zamknij()


START = time.time()
a.after(2500, szukaj)
a.mainloop()
