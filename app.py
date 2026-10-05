"""Nutka - okienko: wyszukujesz albo wklejasz link (YouTube lub Spotify), dostajesz mp3.

YouTube  -> yt-dlp pobiera audio i konwertuje do mp3 (ffmpeg).
Spotify  -> lista utworów (spotapi), każdy dopasowany w YouTube Music i stamtąd pobrany (spotify_lista.py).
Szukaj   -> wyniki z YouTube Music (ytmusicapi), odsłuch przez ffplay.
Exe sam po cichu aktualizuje yt-dlp, ytmusicapi i spotapi (aktualizacje.py), a nową wersję programu
proponuje z GitHub Releases (aktualizacja_programu.py).

MATCODE
"""

import ctypes
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import customtkinter as ctk

import aktualizacja_programu
import aktualizacje
import spotify_lista

WERSJA = "1.1.0"  # jedyne źródło wersji: czyta ją zbuduj.ps1 (instalator, wydanie na GitHubie) i aktualizacja_programu
REPO_GITHUB = "matmiccode/nutka"  # skąd program bierze informację o nowych wersjach (GitHub Releases)
BUYCOFFEE_URL = "https://buycoffee.to/matcode"  # profil na buycoffee.to - pusty = przycisk „Postaw kawę” się nie pokazuje
DOMYSLNY_FOLDER = Path.home() / "Music" / "Pobrane"
PODPIS = "MATCODE"
ROWNOLEGLE_POBIERANIA = 3  # lista Spotify: ile utworów naraz
BEZ_OKNA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CO_ILE_AKTUALIZACJE_MS = 6 * 3600 * 1000  # poza startem - gdyby okno wisiało otwarte dniami
ROZCIAGANE = ("tytul", "wykonawca", "album")  # kolumny tabeli, które dzielą wolne miejsce i skracają się do „…”

# paleta Nutka - ciemny motyw w kolorach ikony (róż -> fiolet)
TLO = "#141019"          # tło okna
KARTA = "#1E1826"        # panele
POLE = "#2A2233"         # pola tekstowe, przyciski drugorzędne
OBRYS = "#3A3045"
TEKST = "#F4EEF7"
TEKST_SZARY = "#A99BB5"
AKCENT = "#E0479E"       # róż z ikony
AKCENT_NAJECHANY = "#C4358A"
WYBRANY = "#5E2656"      # zaznaczony wiersz tabeli - stonowana malina, żeby róż zostawał dla „Pobierz”
BLAD = "#FF8FA8"         # wiersz, którego nie udało się pobrać
FIOLET = "#8E2FB8"       # koniec gradientu nagłówka (naglowek.png)
FONT = "Segoe UI"

SPAKOWANY = getattr(sys, "frozen", False)  # exe z PyInstallera; bez tego = python app.py z build\venv (testy)
FOLDER_PROGRAMU = Path(sys.executable).parent if SPAKOWANY else Path(__file__).parent
ZASOBY = Path(getattr(sys, "_MEIPASS", FOLDER_PROGRAMU))  # ikona itp. - w exe leżą w _internal
if SPAKOWANY:
    aktualizacje.zastosuj()  # musi być przed pierwszym importem yt_dlp/ytmusicapi

# ffmpeg/ffplay/deno: w exe leżą w narzedzia\ (przy testach z venv deno jest obok pythona)
_dodatkowe = [FOLDER_PROGRAMU / "narzedzia", Path(sys.executable).parent]
os.environ["PATH"] = os.pathsep.join([*map(str, _dodatkowe), os.environ.get("PATH", "")])
# procesy potomne exe (--yt-dlp, test aktualizacji) nie pokazują ekranu wczytywania
os.environ["PYINSTALLER_SUPPRESS_SPLASH_SCREEN"] = "1"
ENV_UTF8 = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def zamknij_ekran_startowy():
    """Ekran wczytywania exe (PyInstaller --splash, splash.png): znika, gdy okno gotowe albo od razu w trybie
    bez okna (--autotest itd.). Procesy potomne w ogóle go nie pokazują (PYINSTALLER_SUPPRESS_SPLASH_SCREEN)."""
    try:
        import pyi_splash
        pyi_splash.close()
    except (ImportError, RuntimeError):
        pass


def narzedzie(nazwa: str) -> list[str]:
    """Początek komendy dla yt-dlp. Exe nie ma osobnego Pythona, więc woła sam siebie (--yt-dlp)."""
    if SPAKOWANY:
        return [sys.executable, f"--{nazwa}"]
    return [sys.executable, "-m", {"yt-dlp": "yt_dlp"}[nazwa]]


def wyjscie_utf8():
    """Exe z PyInstallera ignoruje PYTHONUTF8, więc polskie znaki w logu trzeba wymusić ręcznie."""
    for strumien in (sys.stdout, sys.stderr):
        if strumien is not None:
            strumien.reconfigure(encoding="utf-8", errors="replace")


def uruchom_narzedzie(przelacznik: str, argumenty: list[str]):
    """Druga strona narzedzie(): w procesie potomnym exe zamiast okna odpala yt-dlp."""
    wyjscie_utf8()
    import yt_dlp
    sys.exit(yt_dlp.main(argumenty))


def rozpoznaj_zrodlo(link: str) -> str | None:
    link = link.lower()
    if "spotify.com" in link or link.startswith("spotify:"):
        return "spotify"
    if "youtube.com" in link or "youtu.be" in link:
        return "youtube"
    return None


def to_playlista_yt(link: str) -> bool:
    """Czysty link do playlisty/albumu (youtube.com/playlist?list=...).

    Link do pojedynczego filmu z doklejonym &list=... (np. z miksu) traktujemy jak jeden utwór.
    """
    link = link.lower()
    return "/playlist?" in link or "music.youtube.com/browse/" in link


def zbuduj_komende(link: str, folder: Path) -> list[str]:
    zrodlo = rozpoznaj_zrodlo(link)
    if zrodlo == "youtube":
        if to_playlista_yt(link):
            szablon = [
                # YT Music nazywa albumy "Album - Tytuł" - do nazwy folderu wystarczy sam tytuł
                "--replace-in-metadata", "playlist_title", "^(Album|Single|EP) - ", "",
                "-o", "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s",
            ]
        else:
            # "Wykonawca - Tytuł" gdy YT Music zna wykonawcę; zwykłe filmy mają go zwykle już w tytule
            szablon = ["-o", "%(artists.0&{} - |)s%(title)s.%(ext)s", "--no-playlist"]
        return [
            *narzedzie("yt-dlp"),
            "-x", "--audio-format", "mp3", "--audio-quality", "0",
            "--embed-thumbnail", "--embed-metadata",
            # zamiast pełnego logu: tylko nasze znaczniki, które GUI rozumie
            "-q", "--no-warnings", "--no-simulate", "--color", "never",
            "--progress", "--newline",
            "--progress-template", "download:POSTEP %(progress._percent_str)s",
            "--print", "before_dl:UTWOR %(playlist_index|)s/%(n_entries|)s %(title)s",
            "--print", "after_move:PLIK %(filepath)s",
            "-P", str(folder),
            *szablon,
            link,
        ]
    raise ValueError("Nieznany link - obsługiwane są YouTube i Spotify.")  # Spotify idzie przez tryb listy


def komenda_utworu(video_id: str, plik: Path) -> list[str]:
    """Jeden utwór z listy Spotify: dopasowany film YouTube Music -> dokładnie ten plik mp3 (tagi dopisze otaguj())."""
    return [
        *narzedzie("yt-dlp"), "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "-q", "--no-warnings", "--color", "never", "--no-playlist", "--progress", "--newline",
        "--progress-template", "download:POSTEP %(progress._percent_str)s",
        "-o", str(plik.with_suffix("")).replace("%", "%%") + ".%(ext)s",  # % w tytule ≠ pole szablonu yt-dlp
        f"https://music.youtube.com/watch?v={video_id}",
    ]


_watki = threading.local()


def klient_yt_music():
    """Osobny klient YouTube Music na wątek (lista Spotify dopasowuje kilka utworów naraz)."""
    from ytmusicapi import YTMusic  # import dopiero przy pierwszym użyciu - szybszy start okna

    if not hasattr(_watki, "klient"):
        _watki.klient = YTMusic(location="PL")
    return _watki.klient


def szukaj_yt_music(fraza: str, rodzaj: str, ile: int = 15) -> list[dict]:
    """Wyniki z YouTube Music jako słowniki: tytul, wykonawca, album, czas, link."""
    klient = klient_yt_music()
    wyniki = []
    if rodzaj == "Albumy":
        for w in klient.search(fraza, filter="albums", limit=ile)[:ile]:
            if not w.get("playlistId"):
                continue
            wyniki.append({
                "tytul": w.get("title", ""),
                "wykonawca": ", ".join(a["name"] for a in w.get("artists") or []),
                "album": " ".join(filter(None, [w.get("type"), w.get("year")])),
                "czas": "",
                "link": f"https://music.youtube.com/playlist?list={w['playlistId']}",
            })
    else:
        for w in klient.search(fraza, filter="songs", limit=ile)[:ile]:
            if not w.get("videoId"):
                continue
            wyniki.append({
                "tytul": w.get("title", ""),
                "wykonawca": ", ".join(a["name"] for a in w.get("artists") or []),
                "album": (w.get("album") or {}).get("name", ""),
                "czas": w.get("duration", ""),
                "link": f"https://music.youtube.com/watch?v={w['videoId']}",
            })
    return wyniki


class Aplikacja(ctk.CTk):
    def __init__(self):
        # własny identyfikator aplikacji: pasek zadań bierze wtedy naszą ikonę, a nie ikonę pythona
        # (skróty z instalatora mają ten sam AppUserModelID - przypięcie do paska też trafia w Nutka)
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MATCODE.Nutka")
        except (AttributeError, OSError):
            pass
        ctk.set_appearance_mode("dark")  # ciemny też pasek tytułu Windows
        super().__init__(fg_color=TLO)
        self.title("Nutka – MATCODE")
        self.geometry("960x720")
        self.minsize(760, 600)
        self._ustaw_ikone()

        self.kolejka: queue.Queue = queue.Queue()
        self.proces: subprocess.Popen | None = None
        self.odsluch: subprocess.Popen | None = None
        self.odsluch_nr = 0  # numer bieżącego odsłuchu; stary wątek po zmianie numeru się wycofuje
        self.linki_wynikow: dict[str, str] = {}
        self._pelne_teksty: dict[str, dict[str, str]] = {}  # iid -> pełny tytuł/wykonawca/album (w tabeli bywa „…”)
        self._skracanie = None
        self.folder = tk.StringVar(value=str(DOMYSLNY_FOLDER))
        self.link = tk.StringVar()
        self.rodzaj = tk.StringVar(value="Utwory")
        self._tryb_paska = "determinate"
        # tryb listy (Spotify): tabela pokazuje utwory z playlisty/albumu z ptaszkami zamiast wyników wyszukiwania
        self.lista: spotify_lista.Lista | None = None
        self.wiersze_listy: dict[str, spotify_lista.Utwor] = {}
        self.zaznaczone: set[str] = set()
        self.pobieranie_listy = False
        self.przerwij_liste = threading.Event()
        self.procesy_listy: set[subprocess.Popen] = set()
        self.okno_aktualizacji: ctk.CTkToplevel | None = None

        self._zbuduj_ui()
        self.protocol("WM_DELETE_WINDOW", self._zamknij)
        self.after(100, self._odbierz_logi)
        self.after(150, self._kolor_paska_tytulu)
        if SPAKOWANY:
            self.after(200, self._po_ekranie_startowym)  # okno już narysowane
            self.after(3000, self._aktualizuj)

    def _kolor_paska_tytulu(self):
        """Windows 11: pasek tytułu w kolorze tła okna (na Windows 10 po prostu ciemny - ignoruje atrybut)."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            r, g, b = (int(TLO[i:i + 2], 16) for i in (1, 3, 5))
            kolor = ctypes.c_int(r | g << 8 | b << 16)  # COLORREF = 0x00BBGGRR
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(kolor), 4)  # DWMWA_CAPTION_COLOR
        except (AttributeError, OSError):
            pass

    def _ustaw_ikone(self):
        ikona = ZASOBY / "ikona.ico"
        if ikona.exists():
            self.iconbitmap(default=str(ikona))  # default = też okna dialogowe

    def _po_ekranie_startowym(self):
        zamknij_ekran_startowy()
        # ekran wczytywania PyInstallera używa tego samego Tk i gubi ikonę okna (zostaje piórko Tk) - ustawiamy ją jeszcze raz
        self._ustaw_ikone()

    # ---------- wygląd ----------

    def _przycisk(self, rodzic, tekst: str, polecenie, glowny: bool = False, **opcje) -> ctk.CTkButton:
        """Główny = różowy (Szukaj, Pobierz), reszta = ciemny z jaśniejszym najechaniem."""
        return ctk.CTkButton(
            rodzic, text=tekst, command=polecenie, corner_radius=10, height=opcje.pop("height", 36),
            fg_color=AKCENT if glowny else POLE, hover_color=AKCENT_NAJECHANY if glowny else OBRYS,
            text_color=TEKST, text_color_disabled=TEKST_SZARY,
            font=ctk.CTkFont(FONT, 14, "bold" if glowny else "normal"), **opcje)

    def _pole(self, rodzic, **opcje) -> ctk.CTkEntry:
        return ctk.CTkEntry(rodzic, height=38, corner_radius=10, border_width=1, fg_color=POLE, border_color=OBRYS,
                            text_color=TEKST, placeholder_text_color=TEKST_SZARY, font=ctk.CTkFont(FONT, 14), **opcje)

    def _przycisk_kawy(self, naglowek: ctk.CTkFrame, gradient, margines: int) -> ctk.CTkLabel:
        """Biała pigułka w nagłówku: „Postaw kawę autorowi” + niżej mały podpis MATCODE (dobrowolne wsparcie).
        Rysowana w Pillow (2x pod DPI) na wycinku gradientu, który leży dokładnie pod nią - zaokrąglone rogi CTk
        mają jeden kolor tła, a gradient pod pigułką przechodzi z różu w fiolet, więc rogi wychodziły kanciaste."""
        from PIL import Image, ImageDraw, ImageFont
        szer, wys, gora_y = 196, 52, 16  # px logiczne; nagłówek ma 84, pigułka na środku
        try:
            duza, mala = ImageFont.truetype("segoeuib.ttf", 28), ImageFont.truetype("segoeuib.ttf", 21)
        except (OSError, ImportError):  # brak czcionki albo FreeType w paczce - prosty krój zamiast błędu
            duza = mala = ImageFont.load_default()
        przycisk = ctk.CTkLabel(naglowek, text="", width=szer, height=wys, fg_color=FIOLET, cursor="hand2")
        przycisk.place(relx=1.0, x=-margines, y=gora_y, anchor="ne")
        obrazy: dict[tuple[int, bool], ctk.CTkImage] = {}
        stan = {"najechany": False}

        def narysuj(_=None):
            x = round((naglowek.winfo_width() / self._skala - margines - szer) * 2)  # naglowek.png jest 2x
            klucz = (x, stan["najechany"])
            if klucz not in obrazy:
                if len(obrazy) > 40:  # przeciąganie krawędzi okna = dziesiątki pozycji
                    obrazy.clear()
                W, H = szer * 2, wys * 2
                obraz = Image.new("RGB", (W, H), FIOLET)  # za prawym końcem naglowek.png nagłówek jest FIOLET
                widoczne = min(W, gradient.width - x) if gradient is not None else 0
                if widoczne > 0:
                    obraz.paste(gradient.crop((x, gora_y * 2, x + widoczne, gora_y * 2 + H)))
                maska = Image.new("L", (W * 2, H * 2))  # podwójna rozdzielczość -> gładkie rogi po zmniejszeniu
                ImageDraw.Draw(maska).rounded_rectangle((0, 0, W * 2 - 1, H * 2 - 1), radius=H, fill=255)
                obraz.paste("#F6E6F3" if stan["najechany"] else "#FFFFFF", mask=maska.resize((W, H), Image.LANCZOS))
                rysuj = ImageDraw.Draw(obraz)
                rysuj.text((W / 2, H * 0.40), "Postaw kawę autorowi", font=duza, fill=FIOLET, anchor="mm")
                rysuj.text((W / 2, H * 0.73), "MATCODE", font=mala, fill=AKCENT, anchor="mm")
                obrazy[klucz] = ctk.CTkImage(obraz, size=(szer, wys))
            przycisk.configure(image=obrazy[klucz])

        def najechanie(tak: bool):
            stan["najechany"] = tak
            narysuj()
        naglowek.bind("<Configure>", narysuj, add="+")
        przycisk.bind("<Button-1>", lambda _: webbrowser.open(BUYCOFFEE_URL))
        przycisk.bind("<Enter>", lambda _: najechanie(True))
        przycisk.bind("<Leave>", lambda _: najechanie(False))
        return przycisk

    def _styl_tabeli(self):
        """Tabela wyników to ttk.Treeview (CustomTkinter nie ma tabeli) - ubieramy ją w te same kolory."""
        try:
            skala = self._get_window_scaling()
        except AttributeError:
            skala = 1.0
        self._skala = skala  # Treeview liczy w pikselach fizycznych - szerokości kolumn też trzeba przeskalować
        styl = ttk.Style(self)
        styl.theme_use("clam")  # tylko "clam" pozwala przemalować nagłówki kolumn
        styl.layout("Nutka.Treeview", [("Nutka.Treeview.treearea", {"sticky": "nswe"})])  # bez ramki
        self._czcionka_wierszy = tkfont.Font(self, family=FONT, size=11)  # ta sama co w wierszach - do skracania „…”
        styl.configure("Nutka.Treeview", background=KARTA, fieldbackground=KARTA, foreground=TEKST,
                       rowheight=int(32 * skala), borderwidth=0, font=self._czcionka_wierszy)
        styl.map("Nutka.Treeview", background=[("selected", WYBRANY)], foreground=[("selected", "#FFFFFF")])
        # padding nagłówka = wcięcie tekstu w komórkach, inaczej nazwy kolumn stoją kilka pikseli obok treści
        styl.configure("Nutka.Treeview.Heading", background=KARTA, foreground=TEKST_SZARY, relief="flat",
                       borderwidth=0, font=(FONT, 10, "bold"), padding=(4, int(6 * skala)))
        styl.map("Nutka.Treeview.Heading", background=[("active", KARTA)])

    def _zbuduj_ui(self):
        self._styl_tabeli()
        self.columnconfigure(0, weight=1)
        margines = 18

        # --- nagłówek: gradient z nutką i nazwą (naglowek.png; nadmiar po prawej przycięty, dalej kolor FIOLET) ---
        naglowek = ctk.CTkFrame(self, height=84, corner_radius=0, fg_color=FIOLET)
        naglowek.grid(row=0, column=0, sticky="ew")
        naglowek.grid_propagate(False)
        plik_naglowka = ZASOBY / "naglowek.png"
        obraz = None
        if plik_naglowka.exists():
            from PIL import Image
            obraz = Image.open(plik_naglowka).convert("RGB")
            ctk.CTkLabel(naglowek, text="", image=ctk.CTkImage(obraz, size=(obraz.width // 2, obraz.height // 2))
                         ).place(x=0, y=0)
        if BUYCOFFEE_URL:
            self._przycisk_kawy(naglowek, obraz, margines)

        # --- wyszukiwarka ---
        wiersz_szukaj = ctk.CTkFrame(self, fg_color="transparent")
        wiersz_szukaj.grid(row=1, column=0, sticky="ew", padx=margines, pady=(margines, 10))
        wiersz_szukaj.columnconfigure(0, weight=1)
        self.pole_szukaj = self._pole(wiersz_szukaj, placeholder_text="Wpisz tytuł lub wykonawcę – albo wklej link do utworu, albumu lub playlisty (YouTube, Spotify)")
        self.pole_szukaj.grid(row=0, column=0, sticky="ew")
        self.pole_szukaj.bind("<Return>", lambda _: self.szukaj())
        self.after(300, self.pole_szukaj.focus)
        ctk.CTkSegmentedButton(
            wiersz_szukaj, values=["Utwory", "Albumy"], variable=self.rodzaj, height=38, corner_radius=10,
            fg_color=POLE, unselected_color=POLE, unselected_hover_color=OBRYS, selected_color=AKCENT,
            selected_hover_color=AKCENT_NAJECHANY, text_color=TEKST, font=ctk.CTkFont(FONT, 13),
        ).grid(row=0, column=1, padx=(10, 0))
        self.przycisk_szukaj = self._przycisk(wiersz_szukaj, "Szukaj", self.szukaj, glowny=True, width=110, height=38)
        self.przycisk_szukaj.grid(row=0, column=2, padx=(10, 0))

        # --- wyniki ---
        karta_wynikow = ctk.CTkFrame(self, fg_color=KARTA, corner_radius=14)
        karta_wynikow.grid(row=2, column=0, sticky="nsew", padx=margines)
        karta_wynikow.columnconfigure(0, weight=1)
        karta_wynikow.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)  # całe wolne miejsce w pionie dostaje tabela (log ma stałą wysokość)

        # pasek trybu listy (Spotify) - widoczny tylko, gdy tabela pokazuje playlistę/album
        self.pasek_listy = ctk.CTkFrame(karta_wynikow, fg_color="transparent")
        self.pasek_listy.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 0))
        self.opis_listy = ctk.CTkLabel(self.pasek_listy, text="", text_color=TEKST, anchor="w",
                                       font=ctk.CTkFont(FONT, 14, "bold"))
        self.opis_listy.pack(side="left", fill="x", expand=True)
        maly_przycisk = dict(width=10, height=30)
        self._przycisk(self.pasek_listy, "Zamknij listę", self.zamknij_liste, **maly_przycisk).pack(side="right")
        self._przycisk(self.pasek_listy, "Odznacz wszystko", lambda: self._zaznacz_wszystko(False),
                       **maly_przycisk).pack(side="right", padx=6)
        self._przycisk(self.pasek_listy, "Zaznacz wszystko", lambda: self._zaznacz_wszystko(True),
                       **maly_przycisk).pack(side="right")
        self.pasek_listy.grid_remove()

        # szerokości minimalne - wolne miejsce dostają tytuł/wykonawca/album (stretch); razem muszą się zmieścić
        # w najwęższym oknie także w trybie listy (z ptaszkiem i statusem), inaczej CZAS/STATUS uciekają za krawędź
        kolumny = {"wybor": ("", 36), "tytul": ("Tytuł", 170), "wykonawca": ("Wykonawca", 120),
                   "album": ("Album", 120), "czas": ("Czas", 56), "status": ("Status", 140)}
        self.wyniki = ttk.Treeview(karta_wynikow, columns=list(kolumny), show="headings", height=4,
                                   selectmode="browse", style="Nutka.Treeview")
        self._szerokosci = {klucz: szer for klucz, (_, szer) in kolumny.items()}
        for klucz, (naglowek_kol, szer) in kolumny.items():
            kotwica = {"czas": "e", "wybor": "center"}.get(klucz, "w")
            self.wyniki.heading(klucz, text=naglowek_kol, anchor=kotwica)
            self.wyniki.column(klucz, width=szer, anchor=kotwica, stretch=False)  # rozkład robi _dopasuj_kolumny
        self.wyniki.heading("wybor", text="☑", command=self._przelacz_wszystkie)
        self._pokaz_kolumny(("tytul", "wykonawca", "album", "czas"))  # tryb wyszukiwania
        self.wyniki.tag_configure("parzysty", background="#231C2C")  # delikatne paski co drugi wiersz
        self.wyniki.tag_configure("odznaczony", foreground=TEKST_SZARY)
        self.wyniki.tag_configure("blad", foreground=BLAD)  # po tagu odznaczony - nieudany wiersz zawsze widać
        self.wyniki.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=10)
        suwak_wyn = ctk.CTkScrollbar(karta_wynikow, command=self.wyniki.yview, button_color=OBRYS,
                                     button_hover_color=AKCENT)
        suwak_wyn.grid(row=1, column=1, sticky="ns", padx=4, pady=10)
        self.wyniki.configure(yscrollcommand=suwak_wyn.set)
        self.wyniki.bind("<<TreeviewSelect>>", self._wybrano_wynik)
        self.wyniki.bind("<Double-1>", self._dwuklik)
        self.wyniki.bind("<Button-1>", self._klik_w_tabeli, add="+")
        self.wyniki.bind("<Configure>", lambda _: self._dopasuj_kolumny(), add="+")
        # pusta tabela = zachęta: co zrobić najpierw, pod spodem jak obsługiwać wyniki
        self.pusta_tabela = ctk.CTkFrame(karta_wynikow, fg_color=KARTA)
        ctk.CTkLabel(self.pusta_tabela, text="♫", text_color=AKCENT, font=ctk.CTkFont(FONT, 34)).pack()
        self.pusta_tytul = ctk.CTkLabel(self.pusta_tabela, text="", text_color=TEKST, font=ctk.CTkFont(FONT, 17, "bold"))
        self.pusta_tytul.pack(pady=(2, 6))
        self.pusta_opis = ctk.CTkLabel(self.pusta_tabela, text="", text_color=TEKST_SZARY, font=ctk.CTkFont(FONT, 13),
                                       justify="center")
        self.pusta_opis.pack()
        self._pokaz_pusta()

        # --- link i folder ---
        karta_linku = ctk.CTkFrame(self, fg_color="transparent")
        karta_linku.grid(row=3, column=0, sticky="ew", padx=margines, pady=(12, 0))
        karta_linku.columnconfigure(1, weight=1)
        opis = dict(text_color=TEKST_SZARY, font=ctk.CTkFont(FONT, 13))
        ctk.CTkLabel(karta_linku, text="Link", **opis).grid(row=0, column=0, sticky="w", padx=(2, 12))
        pole_link = self._pole(karta_linku, textvariable=self.link)
        pole_link.grid(row=0, column=1, sticky="ew")
        pole_link.bind("<Return>", lambda _: self.pobierz())
        self._przycisk(karta_linku, "Wklej", self._wklej, width=120, height=38).grid(row=0, column=2, padx=(10, 0))
        ctk.CTkLabel(karta_linku, text="Zapisz do", **opis).grid(row=1, column=0, sticky="w", padx=(2, 12), pady=(8, 0))
        self._pole(karta_linku, textvariable=self.folder).grid(row=1, column=1, sticky="ew", pady=(8, 0))
        self._przycisk(karta_linku, "Wybierz…", self._wybierz_folder, width=120, height=38).grid(
            row=1, column=2, padx=(10, 0), pady=(8, 0))

        # --- przyciski i pasek postępu ---
        przyciski = ctk.CTkFrame(self, fg_color="transparent")
        przyciski.grid(row=4, column=0, sticky="ew", padx=margines, pady=14)
        self.przycisk_pobierz = self._przycisk(przyciski, "Pobierz mp3", self.pobierz, glowny=True, width=150, height=42)
        self.przycisk_pobierz.pack(side="left")
        self.przycisk_odsluch = self._przycisk(przyciski, "▶  Odsłuchaj", self.odsluchaj, width=130, height=42)
        self.przycisk_odsluch.pack(side="left", padx=(10, 0))
        self.przycisk_nastepny = self._przycisk(przyciski, "Następny  ›", self._nastepny, width=110, height=42,
                                                state="disabled")
        self.przycisk_nastepny.pack(side="left", padx=(6, 0))
        self._przycisk(przyciski, "Otwórz folder", self._otworz_folder, width=130, height=42).pack(side="left", padx=(6, 0))
        self.pasek = ctk.CTkProgressBar(przyciski, height=8, corner_radius=4, fg_color=POLE, progress_color=POLE,
                                        mode="determinate")  # różowieje dopiero przy pobieraniu (_ustaw_postep)
        self.pasek.set(0)  # w spoczynku pusty
        self.pasek.pack(side="left", fill="x", expand=True, padx=(18, 0))

        # --- log ---
        self.log = ctk.CTkTextbox(self, height=92, corner_radius=14, fg_color=KARTA, text_color=TEKST_SZARY,
                                  font=ctk.CTkFont(FONT, 13), wrap="word", state="disabled",
                                  scrollbar_button_color=OBRYS, scrollbar_button_hover_color=AKCENT)
        self.log.grid(row=5, column=0, sticky="ew", padx=margines)

        # --- stopka ---
        stopka = ctk.CTkFrame(self, fg_color="transparent")
        stopka.grid(row=6, column=0, sticky="ew", padx=margines + 2, pady=(8, 10))
        maly = dict(text_color=TEKST_SZARY, font=ctk.CTkFont(FONT, 12))
        # klik w wersję = ręczne „Sprawdź aktualizacje”
        self.stopka_wersja = ctk.CTkLabel(stopka, text=self._opis_wersji(), cursor="hand2", **maly)
        self.stopka_wersja.pack(side="left")
        self.stopka_wersja.bind("<Button-1>", lambda _: self.sprawdz_wersje_programu(recznie=True))
        ctk.CTkLabel(stopka, text=PODPIS, **maly).pack(side="right")

    @staticmethod
    def _opis_wersji() -> str:
        wersja = aktualizacje.wersja("yt-dlp")  # nightly: 2026.9.27.232945.dev0 -> "2026.9.27 (nightly)"
        silnik = f"{'.'.join(wersja.split('.')[:3])}{' nightly' if 'dev' in wersja else ''}"
        return f"Nutka {WERSJA}  ·  silnik yt-dlp {silnik}  ·  sprawdź aktualizacje"

    # ---------- ciche aktualizacje (tylko exe) ----------

    def _aktualizuj(self):
        threading.Thread(target=self._aktualizuj_w_tle, daemon=True).start()
        self.after(CO_ILE_AKTUALIZACJE_MS, self._aktualizuj)

    def _aktualizuj_w_tle(self):
        self.sprawdz_wersje_programu()  # nowa wersja Nutki na GitHubie -> okienko z propozycją
        try:
            nowe = aktualizacje.aktualizuj(narzedzie("yt-dlp")[:1])
            if nowe:
                aktualizacje.zapisz_log(f"zaktualizowano: {nowe}")
                self.kolejka.put(("wersja", self._opis_wersji()))
        except Exception as e:
            # brak internetu / PyPI zablokowane / zła wersja - zostaje to, co działa
            aktualizacje.zapisz_log(f"bez zmian, błąd: {e!r}")

    # ---------- aktualizacja samego programu (GitHub Releases) ----------

    def sprawdz_wersje_programu(self, recznie: bool = False):
        """Automatycznie: w tle i po cichu. Ręcznie (klik w wersję w stopce): z komunikatem także, gdy brak nowej."""
        def w_tle():
            try:
                wydanie = aktualizacja_programu.do_zaproponowania(REPO_GITHUB, WERSJA, recznie)
            except Exception as e:
                wydanie = None
                if recznie:
                    self.kolejka.put(("log", f"✖ Nie udało się sprawdzić aktualizacji: {e}"))
                    return
            if wydanie:
                self.kolejka.put(("nowa_wersja", wydanie))
            elif recznie:
                self.kolejka.put(("log", f"✔ Masz najnowszą wersję Nutki ({WERSJA})."))
        if recznie:
            self._dopisz("Sprawdzam, czy jest nowa wersja Nutki…")
        threading.Thread(target=w_tle, daemon=True).start()

    def _pokaz_nowa_wersje(self, wydanie: dict):
        if self.okno_aktualizacji is not None and self.okno_aktualizacji.winfo_exists():
            return
        okno = self.okno_aktualizacji = ctk.CTkToplevel(self, fg_color=TLO)
        okno.title("Aktualizacja Nutki")
        okno.geometry("560x430")
        okno.resizable(False, False)
        okno.transient(self)
        okno.after(250, lambda: (okno.iconbitmap(str(ZASOBY / "ikona.ico")) if (ZASOBY / "ikona.ico").exists() else None,
                                 okno.lift(), okno.focus_force()))
        ctk.CTkLabel(okno, text=f"Dostępna jest nowa wersja Nutki {wydanie['wersja']}", text_color=TEKST,
                     font=ctk.CTkFont(FONT, 18, "bold")).pack(anchor="w", padx=22, pady=(20, 2))
        ctk.CTkLabel(okno, text=f"Masz wersję {WERSJA}. Aktualizacja zajmie około minuty, Twoje pliki zostają.",
                     text_color=TEKST_SZARY, font=ctk.CTkFont(FONT, 13)).pack(anchor="w", padx=22)
        ctk.CTkLabel(okno, text="Co nowego:", text_color=TEKST, font=ctk.CTkFont(FONT, 13, "bold")).pack(
            anchor="w", padx=22, pady=(14, 4))
        opis = ctk.CTkTextbox(okno, height=170, corner_radius=10, fg_color=KARTA, text_color=TEKST_SZARY,
                              font=ctk.CTkFont(FONT, 13), wrap="word")
        opis.pack(fill="x", padx=22)
        tresc = re.sub(r"^#+\s*", "", wydanie["opis"].strip(), flags=re.M).replace("**", "")
        tresc = re.sub(r"^\s*[-*]\s+", "•  ", tresc, flags=re.M)  # markdownowe punkty -> kropki
        opis.insert("end", tresc or "Poprawki i ulepszenia.")
        opis.configure(state="disabled")
        pasek = ctk.CTkProgressBar(okno, height=8, fg_color=POLE, progress_color=AKCENT)
        pasek.set(0)
        stan = ctk.CTkLabel(okno, text="", text_color=TEKST_SZARY, font=ctk.CTkFont(FONT, 12))
        przyciski = ctk.CTkFrame(okno, fg_color="transparent")
        przyciski.pack(fill="x", padx=22, pady=(16, 18), side="bottom")

        def pomin():
            aktualizacja_programu.zapisz_ustawienie("pominieta_wersja", wydanie["wersja"])
            okno.destroy()

        def zaktualizuj():
            if (self.proces or self.pobieranie_listy) and not messagebox.askyesno(
                    "Aktualizacja", "Trwa pobieranie - przerwać je i zaktualizować teraz?", parent=okno):
                return
            for p in przyciski.winfo_children():
                p.configure(state="disabled")
            pasek.pack(fill="x", padx=22, pady=(14, 2))
            stan.pack(anchor="w", padx=22)
            stan.configure(text="Pobieram nową wersję…")

            def w_tle():
                try:
                    plik = aktualizacja_programu.pobierz_instalator(
                        wydanie, lambda p: self.kolejka.put(("aktualizacja_postep", (pasek, stan, p))))
                    self.kolejka.put(("aktualizacja_gotowa", plik))
                except Exception as e:
                    self.kolejka.put(("aktualizacja_blad", (okno, str(e))))
            threading.Thread(target=w_tle, daemon=True).start()

        self._przycisk(przyciski, "Zaktualizuj teraz", zaktualizuj, glowny=True, width=170).pack(side="right")
        self._przycisk(przyciski, "Przypomnij później", okno.destroy, width=10).pack(side="right", padx=8)
        self._przycisk(przyciski, "Pomiń tę wersję", pomin, width=10).pack(side="left")

    def _zainstaluj_aktualizacje(self, plik: Path):
        """Instalator /SILENT sam zamknie, zainstaluje i uruchomi nową wersję - my tylko znikamy."""
        aktualizacja_programu.uruchom_instalator(plik)
        self._zamknij()

    # ---------- schowek, folder, log ----------

    def _wklej(self):
        try:
            tekst = self.clipboard_get().strip()
        except tk.TclError:
            return
        self.link.set(tekst)
        if rozpoznaj_zrodlo(tekst) == "spotify":
            self.wczytaj_spotify(tekst)  # playlista/album -> od razu lista do przejrzenia

    def _wybierz_folder(self):
        wybrany = filedialog.askdirectory(initialdir=self.folder.get())
        if wybrany:
            self.folder.set(wybrany)

    def _otworz_folder(self):
        folder = Path(self.folder.get())
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def _dopisz(self, tekst: str):
        self.log.configure(state="normal")
        self.log.insert("end", tekst + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------- wyszukiwarka ----------

    def szukaj(self):
        fraza = self.pole_szukaj.get().strip()
        if not fraza:
            return
        # wklejony link w polu szukania = od razu do pola "Link" (Spotify: wczytanie listy utworów)
        if rozpoznaj_zrodlo(fraza):
            self.link.set(fraza)
            if rozpoznaj_zrodlo(fraza) == "spotify":
                self.wczytaj_spotify(fraza)
            return
        self.przycisk_szukaj.configure(state="disabled")
        self._dopisz(f"🔍 Szukam: {fraza}")
        threading.Thread(target=self._szukaj_w_tle, args=(fraza, self.rodzaj.get()), daemon=True).start()

    def _szukaj_w_tle(self, fraza: str, rodzaj: str):
        try:
            self.kolejka.put(("wyniki", szukaj_yt_music(fraza, rodzaj)))
        except Exception as e:
            self.kolejka.put(("log", f"✖ Wyszukiwanie nie wyszło: {e}"))
            self.kolejka.put(("wyniki", None))

    def _pokaz_wyniki(self, wyniki: list[dict] | None):
        self.przycisk_szukaj.configure(state="normal")
        if wyniki is None:
            return
        if self.lista:
            if self.pobieranie_listy:
                self._dopisz("Najpierw poczekaj na koniec pobierania listy (albo kliknij „Zatrzymaj”).")
                return
            self.zamknij_liste()
        self._wyczysc_tabele()
        self.linki_wynikow.clear()
        for i, w in enumerate(wyniki):
            iid = self._wstaw_wiersz(i, w["tytul"], w["wykonawca"], w["album"], w["czas"])
            self.linki_wynikow[iid] = w["link"]
        if wyniki:
            self.pusta_tabela.place_forget()
        else:
            self._pokaz_pusta("Nic nie znaleziono", "Sprawdź pisownię albo wpisz samego wykonawcę.\n"
                                                    "Szukasz całej płyty? Przełącz na „Albumy”.")

    def _wybrano_wynik(self, _=None):
        zaznaczone = self.wyniki.selection()
        if zaznaczone:
            if not self.lista:  # w trybie listy pole „Link” zostaje linkiem do playlisty
                self.link.set(self.linki_wynikow[zaznaczone[0]])
            if self.przycisk_odsluch.cget("text").startswith("■"):  # coś gra -> przełącz na nowy utwór
                self._zatrzymaj_odsluch()
                self.odsluchaj()

    def _dwuklik(self, zdarzenie):
        if self.lista:  # lista: dwuklik = zaznacz/odznacz
            wiersz = self.wyniki.identify_row(zdarzenie.y)
            if wiersz:
                self._przelacz(wiersz)
        else:
            self.pobierz()

    def _klik_w_tabeli(self, zdarzenie):
        """Lista: klik w kolumnę z ptaszkiem przełącza utwór."""
        if self.lista and self.wyniki.identify_region(zdarzenie.x, zdarzenie.y) == "cell" \
                and self.wyniki.identify_column(zdarzenie.x) == "#1":
            wiersz = self.wyniki.identify_row(zdarzenie.y)
            if wiersz:
                self._przelacz(wiersz)

    # ---------- tryb listy (playlista / album / utwór ze Spotify) ----------

    def wczytaj_spotify(self, link: str):
        if self.pobieranie_listy:
            self._dopisz("Trwa pobieranie listy - poczekaj albo kliknij „Zatrzymaj”.")
            return
        if not spotify_lista.rozpoznaj(link):
            messagebox.showinfo("Spotify", "To nie wygląda na link do utworu, albumu ani playlisty Spotify.\n"
                                           "W Spotify: … → Udostępnij → Kopiuj link.")
            return
        self._dopisz("Wczytuję listę utworów ze Spotify…")
        self.przycisk_pobierz.configure(state="disabled")
        self._ustaw_postep(None)

        def w_tle():
            try:
                self.kolejka.put(("lista", (link, spotify_lista.wczytaj(link))))
            except Exception as e:
                self.kolejka.put(("log", f"✖ Nie udało się wczytać listy ze Spotify ({e}). Czy playlista jest "
                                         "publiczna? Prywatnych playlist i „Polubionych” program nie widzi."))
                self.kolejka.put(("koniec", None))
        threading.Thread(target=w_tle, daemon=True).start()

    def _pokaz_liste(self, link: str, lista: spotify_lista.Lista):
        self._ustaw_postep(0)
        self.pasek.configure(progress_color=POLE)
        self.przycisk_pobierz.configure(state="normal")
        self.lista = lista
        self.wiersze_listy.clear()
        self.zaznaczone.clear()
        self._wyczysc_tabele()
        self._pokaz_kolumny(("wybor", "tytul", "wykonawca", "album", "czas", "status"))
        self.pusta_tabela.place_forget()
        folder = Path(self.folder.get())
        masz = 0
        for i, utwor in enumerate(lista.utwory):
            jest = spotify_lista.sciezka_pliku(utwor, lista, folder).exists()  # synchronizacja: to już masz
            masz += jest
            iid = self._wstaw_wiersz(i, utwor.tytul, utwor.wykonawca, utwor.album, utwor.czas, "masz już" if jest else "")
            self.wiersze_listy[iid] = utwor
            self._ustaw_zaznaczenie(iid, not jest)
        self.pasek_listy.grid()
        rodzaj = {"playlista": "Playlista", "album": "Album", "utwór": "Utwór"}[lista.rodzaj]
        opis = f"{rodzaj} „{lista.nazwa}”  ·  {len(lista.utwory)} utw."
        self.opis_listy.configure(text=opis + (f"  ·  {masz} już masz" if masz else ""))
        self._dopisz(f"♫ {opis}" + (f" – {masz} już masz, są odznaczone." if masz else "")
                     + " Odznacz, czego nie chcesz, i kliknij „Pobierz zaznaczone”.")

    def _pokaz_kolumny(self, kolumny: tuple[str, ...]):
        """Zmiana trybu tabeli. Szerokości wracają do bazowych - inaczej Tk zostawia te rozciągnięte w poprzednim
        trybie i nowe kolumny (CZAS, STATUS) lądują za prawą krawędzią."""
        self.wyniki.configure(displaycolumns=kolumny)
        self._dopasuj_kolumny()

    def _dopasuj_kolumny(self):
        """Stałe kolumny (☑, CZAS, STATUS) mają swoją szerokość, a resztę miejsca dzielą proporcjonalnie
        TYTUŁ / WYKONAWCA / ALBUM. Wbudowane „stretch” Tk po zmianie trybu zostawiało kolumny za krawędzią."""
        widoczne = self.wyniki.cget("displaycolumns")
        widoczne = list(self._szerokosci) if widoczne in ("#all", ("#all",)) else list(widoczne)
        baza = {k: int(self._szerokosci[k] * self._skala) for k in widoczne}
        rozciagane = [k for k in widoczne if k in ROZCIAGANE]
        wolne = max(0, self.wyniki.winfo_width() - 4 - sum(baza.values()))
        suma = sum(baza[k] for k in rozciagane)
        for k in widoczne:
            self.wyniki.column(k, width=baza[k] + (wolne * baza[k] // suma if k in rozciagane else 0))
        # przy przeciąganiu krawędzi okna Configure leci seriami - skracamy teksty raz, po chwili spokoju
        if self._skracanie:
            self.after_cancel(self._skracanie)
        self._skracanie = self.after(60, self._skroc_wiersze)

    def _wstaw_wiersz(self, nr: int, tytul: str, wykonawca: str, album: str, czas: str, status: str = "") -> str:
        """Wiersz tabeli - wartości dla WSZYSTKICH kolumn (wybor, tytul, wykonawca, album, czas, status), ukryte też
        liczą się do kolejności. Pełne teksty zostają w _pelne_teksty, w tabeli mogą być skrócone do „…”."""
        iid = self.wyniki.insert("", "end", values=("", tytul, wykonawca, album, czas, status),
                                 tags=("parzysty",) if nr % 2 else ())
        self._pelne_teksty[iid] = {"tytul": tytul, "wykonawca": wykonawca, "album": album}
        self._skroc_wiersze([iid])
        return iid

    def _wyczysc_tabele(self):
        self.wyniki.delete(*self.wyniki.get_children())
        self._pelne_teksty.clear()

    def _skroc_wiersze(self, wiersze=None):
        """Treeview obcina za długi tekst w pół litery - zamiast tego „…” po ostatnim mieszczącym się znaku."""
        if wiersze is None:
            self._skracanie = None
        czcionka = self._czcionka_wierszy
        margines = int(14 * self._skala)  # wcięcie tekstu w komórce z obu stron
        szerokosci = {k: self.wyniki.column(k, "width") - margines for k in ROZCIAGANE}

        def skroc(tekst: str, szer: int) -> str:
            if czcionka.measure(tekst) <= szer:
                return tekst
            od, do = 0, len(tekst)  # najdłuższy początek, który z „…” się mieści
            while od < do:
                srodek = (od + do + 1) // 2
                od, do = (srodek, do) if czcionka.measure(tekst[:srodek].rstrip() + "…") <= szer else (od, srodek - 1)
            return tekst[:od].rstrip() + "…"

        for iid in wiersze if wiersze is not None else list(self._pelne_teksty):
            if self.wyniki.exists(iid):
                for k, tekst in self._pelne_teksty[iid].items():
                    self.wyniki.set(iid, k, skroc(tekst, szerokosci[k]))

    def _ustaw_status(self, iid: str, tekst: str):
        """Kolumna STATUS; „✗ …” (nie udało się) barwi cały wiersz, żeby było widać, co ponowić."""
        if not self.wyniki.exists(iid):
            return
        self.wyniki.set(iid, "status", tekst)
        tagi = [t for t in self.wyniki.item(iid, "tags") if t != "blad"] + (["blad"] if tekst.startswith("✗") else [])
        self.wyniki.item(iid, tags=tagi)

    def _pokaz_pusta(self, tytul: str = "Czego chcesz posłuchać?",
                     opis: str = "Wpisz tytuł lub wykonawcę i kliknij „Szukaj” – albo wklej link z YouTube lub Spotify.\n"
                                 "Klik w wynik wybiera utwór, dwuklik od razu go pobiera."):
        self.pusta_tytul.configure(text=tytul)
        self.pusta_opis.configure(text=opis)
        self.pusta_tabela.place(relx=0.5, rely=0.55, anchor="center")

    def zamknij_liste(self):
        if self.pobieranie_listy:
            self._dopisz("Najpierw zatrzymaj pobieranie listy.")
            return
        self.lista = None
        self.wiersze_listy.clear()
        self.zaznaczone.clear()
        self._wyczysc_tabele()
        self._pokaz_kolumny(("tytul", "wykonawca", "album", "czas"))
        self.pasek_listy.grid_remove()
        self.przycisk_pobierz.configure(text="Pobierz mp3")
        self._pokaz_pusta()

    def _ustaw_zaznaczenie(self, iid: str, zaznacz: bool):
        if zaznacz:
            self.zaznaczone.add(iid)
        else:
            self.zaznaczone.discard(iid)
        self.wyniki.set(iid, "wybor", "☑" if zaznacz else "☐")
        tagi = [t for t in self.wyniki.item(iid, "tags") if t != "odznaczony"] + ([] if zaznacz else ["odznaczony"])
        self.wyniki.item(iid, tags=tagi)
        if not self.pobieranie_listy:
            self.przycisk_pobierz.configure(text=f"Pobierz zaznaczone ({len(self.zaznaczone)})")

    def _przelacz(self, iid: str):
        if not self.pobieranie_listy:
            self._ustaw_zaznaczenie(iid, iid not in self.zaznaczone)

    def _zaznacz_wszystko(self, zaznacz: bool):
        if not self.pobieranie_listy:
            for iid in self.wiersze_listy:
                self._ustaw_zaznaczenie(iid, zaznacz)

    def _przelacz_wszystkie(self):
        self._zaznacz_wszystko(len(self.zaznaczone) < len(self.wiersze_listy))

    def pobierz_liste(self):
        """Zaznaczone utwory: dopasowanie w YouTube Music -> mp3 -> tagi i okładka ze Spotify, po kilka naraz."""
        if self.pobieranie_listy:  # przycisk jest wtedy „Zatrzymaj”
            self.przerwij_liste.set()
            for p in list(self.procesy_listy):
                p.kill()
            self._dopisz("Zatrzymuję…")
            return
        do_pobrania = [iid for iid in self.wiersze_listy if iid in self.zaznaczone]
        if not do_pobrania:
            messagebox.showinfo("Pobieranie", "Nic nie jest zaznaczone.")
            return
        lista, folder = self.lista, Path(self.folder.get())
        self.pobieranie_listy = True
        self.przerwij_liste.clear()
        self.przycisk_pobierz.configure(text="Zatrzymaj")
        for iid in do_pobrania:
            self._ustaw_status(iid, "w kolejce")
        self._dopisz(f"▶ Pobieram {len(do_pobrania)} utw. z „{lista.nazwa}” (po {ROWNOLEGLE_POBIERANIA} naraz)…")
        self._ustaw_postep(0)

        def jeden(iid: str) -> bool:
            if self.przerwij_liste.is_set():
                return False
            utwor = self.wiersze_listy[iid]
            plik = spotify_lista.sciezka_pliku(utwor, lista, folder)
            try:
                if plik.exists():
                    self.kolejka.put(("status", (iid, "masz już")))
                    return True
                self.kolejka.put(("status", (iid, "szukam…")))
                if not (utwor.youtube_id or spotify_lista.dopasuj(utwor, klient_yt_music())):
                    self.kolejka.put(("status", (iid, "✗ brak na YouTube")))
                    return False
                plik.parent.mkdir(parents=True, exist_ok=True)
                proces = subprocess.Popen(komenda_utworu(utwor.youtube_id, plik), stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, env=ENV_UTF8, creationflags=BEZ_OKNA)
                self.procesy_listy.add(proces)
                for linia in proces.stdout:
                    tekst = linia.decode("utf-8", errors="replace").strip()
                    if tekst.startswith("POSTEP "):
                        self.kolejka.put(("status", (iid, f"pobieram {tekst.split()[-1]}")))
                kod = proces.wait()
                self.procesy_listy.discard(proces)
                if kod != 0 or not plik.exists():
                    self.kolejka.put(("status", (iid, "✗ przerwano" if self.przerwij_liste.is_set() else "✗ błąd")))
                    return False
                self.kolejka.put(("status", (iid, "zapisuję…")))
                spotify_lista.otaguj(plik, utwor, lista)
                self.kolejka.put(("status", (iid, "✓ pobrano")))
                return True
            except Exception as e:
                self.kolejka.put(("status", (iid, "✗ błąd")))
                self.kolejka.put(("log", f"✖ {utwor.wykonawca} - {utwor.tytul}: {e}"))
                return False

        def w_tle():
            from concurrent.futures import ThreadPoolExecutor, as_completed
            udane, nieudane = [], []
            with ThreadPoolExecutor(ROWNOLEGLE_POBIERANIA) as pula:
                zadania = {pula.submit(jeden, iid): iid for iid in do_pobrania}
                for i, zadanie in enumerate(as_completed(zadania), 1):
                    (udane if zadanie.result() else nieudane).append(zadania[zadanie])
                    self.kolejka.put(("postep_listy", (i, len(do_pobrania))))
            self.kolejka.put(("lista_koniec", (udane, nieudane)))
        threading.Thread(target=w_tle, daemon=True).start()

    def _koniec_listy(self, udane: list[str], nieudane: list[str]):
        self.pobieranie_listy = False
        for iid in udane:
            self._ustaw_zaznaczenie(iid, False)  # zostają zaznaczone tylko nieudane = „spróbuj ponownie”
        self._ustaw_postep(0)
        self.pasek.configure(progress_color=POLE)
        przerwane = self.przerwij_liste.is_set()
        self._dopisz(("■ Zatrzymano. " if przerwane else "✔ Gotowe. ") + f"Pobrano {len(udane)} z {len(udane) + len(nieudane)}.")
        if nieudane and not przerwane:
            self._dopisz(f"Nie udało się {len(nieudane)} – zostały zaznaczone; kliknij „Pobierz zaznaczone”, "
                         "żeby spróbować jeszcze raz.")
        self.przycisk_pobierz.configure(text=f"Pobierz zaznaczone ({len(self.zaznaczone)})")

    # ---------- odsłuch ----------

    def odsluchaj(self):
        if self.przycisk_odsluch.cget("text").startswith("■"):
            self._zatrzymaj_odsluch()
            return
        if not shutil.which("ffplay"):
            messagebox.showwarning("Odsłuch", "Brak ffplay (część ffmpeg) - zainstaluj program ponownie.")
            return
        utwor = None
        if self.lista:  # lista Spotify: odsłuch zaznaczonego wiersza (dopasowanie w YouTube Music w tle)
            wybrane = self.wyniki.selection()
            if not wybrane:
                messagebox.showinfo("Odsłuch", "Kliknij utwór na liście, który chcesz odsłuchać.")
                return
            utwor, link = self.wiersze_listy[wybrane[0]], ""
        else:
            link = self.link.get().strip()
            if rozpoznaj_zrodlo(link) != "youtube":
                messagebox.showinfo("Odsłuch", "Wybierz utwór z wyników albo wklej link z YouTube.")
                return
        self.odsluch_nr += 1
        self.przycisk_odsluch.configure(text="■  Stop", fg_color=AKCENT, hover_color=AKCENT_NAJECHANY)
        self.przycisk_nastepny.configure(state="normal")

        def w_tle(nr: int, link: str):
            if utwor is not None:
                if not (utwor.youtube_id or spotify_lista.dopasuj(utwor, klient_yt_music())):
                    self.kolejka.put(("log", f"✖ Nie znalazłem „{utwor.tytul}” na YouTube Music."))
                    if nr == self.odsluch_nr:
                        self.kolejka.put(("odsluch_koniec", None))
                    return
                link = f"https://music.youtube.com/watch?v={utwor.youtube_id}"
            self._odsluch_w_tle(link, nr)
        threading.Thread(target=w_tle, args=(self.odsluch_nr, link), daemon=True).start()

    @staticmethod
    def _yt_dlp(*argumenty: str) -> subprocess.CompletedProcess:
        return subprocess.run([*narzedzie("yt-dlp"), "-q", "--no-warnings", *argumenty], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", env=ENV_UTF8, creationflags=BEZ_OKNA)

    def _strumien(self, utwor: str) -> tuple[str | None, str]:
        """(tytuł, adres strumienia audio) albo (None, opis błędu)."""
        wynik = self._yt_dlp("--no-playlist", "-f", "bestaudio", "--print", "title", "--print", "urls", utwor)
        linie = wynik.stdout.strip().splitlines()
        if len(linie) < 2:
            return None, wynik.stderr.strip()[-200:]
        return linie[0], linie[-1]

    def _odsluch_w_tle(self, link: str, nr: int):
        """Utwór albo cały album/playlista po kolei. Gra ffplay bez okna; adres następnego utworu
        wyciągamy, gdy leci bieżący - bez kilkusekundowej dziury między utworami."""
        try:
            if to_playlista_yt(link):
                lista = self._yt_dlp("--flat-playlist", "--print", "url", link).stdout.split()
            else:
                lista = [link]
            nastepny = self._strumien(lista[0]) if lista else (None, "pusta playlista")
            for i in range(len(lista)):
                tytul, adres = nastepny
                if nr != self.odsluch_nr:
                    return  # w międzyczasie kliknięto Stop albo inny utwór
                if tytul is None:
                    self.kolejka.put(("log", f"✖ Nie da się odtworzyć: {adres}"))
                else:
                    numer = f"[{i + 1}/{len(lista)}] " if len(lista) > 1 else ""
                    self.kolejka.put(("log", f"🎧 {numer}{tytul}"))
                    self.odsluch = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", adres], creationflags=BEZ_OKNA)
                    if nr != self.odsluch_nr:  # Stop kliknięty w ułamku sekundy przed startem
                        self.odsluch.kill()
                        return
                nastepny = self._strumien(lista[i + 1]) if i + 1 < len(lista) else None
                if tytul is not None:
                    self.odsluch.wait()  # kończy się sam albo przez ⏭ (kill) - wtedy lecimy dalej
        except Exception as e:
            self.kolejka.put(("log", f"✖ Odsłuch nie działa: {e}"))
        finally:
            if nr == self.odsluch_nr:
                self.odsluch = None
                self.kolejka.put(("odsluch_koniec", None))

    def _nastepny(self):
        if self.odsluch:
            self.odsluch.kill()  # wątek odsłuchu sam przejdzie do kolejnego utworu

    def _zatrzymaj_odsluch(self):
        self.odsluch_nr += 1
        if self.odsluch:
            self.odsluch.kill()
            self.odsluch = None
        self.przycisk_odsluch.configure(text="▶  Odsłuchaj", fg_color=POLE, hover_color=OBRYS)
        self.przycisk_nastepny.configure(state="disabled")

    # ---------- pobieranie ----------

    def pobierz(self):
        if self.lista:  # tryb listy: pobierz zaznaczone (albo „Zatrzymaj”)
            self.pobierz_liste()
            return
        if self.proces:
            return
        link = self.link.get().strip()
        if not rozpoznaj_zrodlo(link):
            messagebox.showwarning("Zły link", "Wybierz coś z wyników albo wklej link z YouTube lub Spotify.")
            return
        if rozpoznaj_zrodlo(link) == "spotify":  # Spotify zawsze przez listę: najpierw widzisz, co pobierzesz
            self.wczytaj_spotify(link)
            return
        folder = Path(self.folder.get())
        folder.mkdir(parents=True, exist_ok=True)

        self.przycisk_pobierz.configure(state="disabled")
        self._ustaw_postep(None)
        self._dopisz(f"▶ Start ({rozpoznaj_zrodlo(link)}): {link}")
        threading.Thread(target=self._uruchom, args=(zbuduj_komende(link, folder),), daemon=True).start()

    def _uruchom(self, komenda: list[str]):
        try:
            self.proces = subprocess.Popen(
                komenda,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=ENV_UTF8,
                creationflags=BEZ_OKNA,
            )
            for linia in self.proces.stdout:
                tekst = linia.decode("utf-8", errors="replace").rstrip()
                if tekst:
                    self._przetworz_linie(tekst)
            kod = self.proces.wait()
            self.kolejka.put(("log", "✔ Gotowe." if kod == 0 else f"✖ Błąd (kod {kod}) - szczegóły wyżej."))
        except Exception as e:
            self.kolejka.put(("log", f"✖ Nie udało się uruchomić: {e}"))
        finally:
            self.proces = None
            self.kolejka.put(("koniec", None))

    def _przetworz_linie(self, tekst: str):
        """Zamienia znaczniki z yt-dlp (POSTEP/UTWOR/PLIK) na pasek i krótkie wpisy; resztę przepuszcza."""
        if tekst.startswith("POSTEP "):
            try:
                procent = float(tekst.split()[1].rstrip("%"))
                # 100% = plik ściągnięty, teraz ffmpeg konwertuje -> pasek „mielący”
                self.kolejka.put(("postep", procent if procent < 100 else None))
            except (IndexError, ValueError):
                pass
        elif tekst.startswith("UTWOR "):
            numer, _, tytul = tekst[6:].partition(" ")
            numer = "" if numer in ("/", "NA/NA") else f"[{numer}] "
            self.kolejka.put(("log", f"♪ {numer}{tytul}"))
        elif tekst.startswith("PLIK "):
            # plik gotowy - tytuł już wypisany przy UTWOR, więc tylko pasek wraca do „mielenia”
            self.kolejka.put(("postep", None))
        else:
            self.kolejka.put(("log", tekst))

    def _odbierz_logi(self):
        try:
            while True:
                rodzaj, wartosc = self.kolejka.get_nowait()
                if rodzaj == "koniec":
                    self._ustaw_postep(0)
                    self.pasek.configure(progress_color=POLE)  # w spoczynku niewidoczny
                    self.przycisk_pobierz.configure(state="normal")
                elif rodzaj == "postep":
                    self._ustaw_postep(wartosc)
                elif rodzaj == "wyniki":
                    self._pokaz_wyniki(wartosc)
                elif rodzaj == "odsluch_koniec":
                    self.przycisk_odsluch.configure(text="▶  Odsłuchaj", fg_color=POLE, hover_color=OBRYS)
                    self.przycisk_nastepny.configure(state="disabled")
                elif rodzaj == "wersja":
                    self.stopka_wersja.configure(text=wartosc)
                elif rodzaj == "lista":
                    self._pokaz_liste(*wartosc)
                elif rodzaj == "status":
                    self._ustaw_status(*wartosc)
                elif rodzaj == "postep_listy":
                    zrobione, wszystkie = wartosc
                    self._ustaw_postep(100 * zrobione / wszystkie)
                    self.opis_listy.configure(text=f"{self.opis_listy.cget('text').split('  ·  [')[0]}"
                                                   f"  ·  [{zrobione}/{wszystkie}]")
                elif rodzaj == "lista_koniec":
                    self._koniec_listy(*wartosc)
                elif rodzaj == "nowa_wersja":
                    self._pokaz_nowa_wersje(wartosc)
                elif rodzaj == "aktualizacja_postep":
                    pasek, stan, procent = wartosc
                    if pasek.winfo_exists():
                        pasek.set(procent / 100)
                        stan.configure(text=f"Pobieram nową wersję… {procent:.0f}%")
                elif rodzaj == "aktualizacja_gotowa":
                    self._zainstaluj_aktualizacje(wartosc)
                    return  # okno zamknięte - koniec pętli
                elif rodzaj == "aktualizacja_blad":
                    okno, blad = wartosc
                    if okno.winfo_exists():
                        okno.destroy()
                    messagebox.showerror("Aktualizacja", f"Nie udało się pobrać aktualizacji:\n{blad}")
                else:
                    self._dopisz(wartosc)
        except queue.Empty:
            pass
        self.after(100, self._odbierz_logi)

    def _ustaw_postep(self, procent: float | None):
        """Liczba = pobieranie (pasek z procentami), None = konwersja/tagi (pasek „mielący”)."""
        self.pasek.configure(progress_color=AKCENT)
        if procent is None:
            if self._tryb_paska != "indeterminate":
                self._tryb_paska = "indeterminate"
                self.pasek.configure(mode="indeterminate")
                self.pasek.start()
        else:
            if self._tryb_paska != "determinate":
                self._tryb_paska = "determinate"
                self.pasek.stop()
                self.pasek.configure(mode="determinate")
            self.pasek.set(procent / 100)

    def _zamknij(self):
        self._zatrzymaj_odsluch()
        self.przerwij_liste.set()
        for p in [self.proces, *self.procesy_listy]:
            if p:
                p.kill()
        self.destroy()


def autotest():
    """Nutka.exe --autotest > raport.txt - sprawdza, czy wszystkie części są na miejscu."""
    wyjscie_utf8()
    print(f"Nutka {WERSJA} - autotest ({'exe' if SPAKOWANY else 'skrypt'}), {PODPIS}")
    print(f"pakiety  {aktualizacje.FOLDER} -> {aktualizacje._wczytaj_stan() or 'wbudowane w exe'}")
    log = aktualizacje.FOLDER / "aktualizacje.log"
    if log.exists():
        print("ostatnie aktualizacje:\n  " + "\n  ".join(log.read_text(encoding="utf-8").splitlines()[-5:]))
    for program in ("ffmpeg", "ffprobe", "ffplay", "deno"):
        print(f"{program:8} {shutil.which(program) or 'BRAK!'}")
    r = subprocess.run([*narzedzie("yt-dlp"), "--version"], capture_output=True, text=True, env=ENV_UTF8,
                       creationflags=BEZ_OKNA)
    print(f"yt-dlp   {r.stdout.strip() or 'BŁĄD: ' + r.stderr.strip()[-300:]}")
    try:
        wyniki = szukaj_yt_music("dawid podsiadło", "Utwory", 3)
        print(f"szukanie OK: {', '.join(w['tytul'] for w in wyniki)}")
    except Exception as e:
        print(f"szukanie BŁĄD: {e!r}")
    try:
        lista = spotify_lista.wczytaj("https://open.spotify.com/album/00hXe7ttZI4gjjWYqKAdMX")
        print(f"spotify OK: album „{lista.nazwa}”, {len(lista.utwory)} utw.")
        if "--pobierz" in sys.argv:  # pełna ścieżka listy: dopasuj -> yt-dlp -> tagi, 1 utwór do %TEMP%
            import tempfile
            from mutagen.id3 import ID3
            utwor = lista.utwory[2]
            plik = spotify_lista.sciezka_pliku(utwor, lista, Path(tempfile.mkdtemp(prefix="nutka-test-")))
            plik.parent.mkdir(parents=True, exist_ok=True)
            print(f"dopasowanie: {spotify_lista.dopasuj(utwor, klient_yt_music())}")
            r = subprocess.run(komenda_utworu(utwor.youtube_id, plik), capture_output=True, env=ENV_UTF8,
                               creationflags=BEZ_OKNA)
            spotify_lista.otaguj(plik, utwor, lista)
            tagi = ID3(plik)
            print(f"pobieranie OK: {plik.name}, {plik.stat().st_size // 1024} KB, tytuł={tagi.get('TIT2')}, "
                  f"okładka={len(tagi.getall('APIC')[0].data) // 1024 if tagi.getall('APIC') else 0} KB (kod {r.returncode})")
            shutil.rmtree(plik.parent.parent, ignore_errors=True)
    except Exception as e:
        print(f"spotify BŁĄD: {e!r}")
    try:
        wydanie = aktualizacja_programu.najnowsze_wydanie(REPO_GITHUB)
        print(f"github   najnowsze wydanie: {wydanie['wersja'] if wydanie else 'brak'} (masz {WERSJA})")
    except Exception as e:
        print(f"github   BŁĄD: {e!r}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        zamknij_ekran_startowy()
    if len(sys.argv) > 1 and sys.argv[1] == "--yt-dlp":
        uruchom_narzedzie(sys.argv[1], sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == "--autotest":
        autotest()
    elif len(sys.argv) > 1 and sys.argv[1] == "--wersje":  # test kandydata w aktualizacje.py
        wyjscie_utf8()
        print(json.dumps(aktualizacje.wersje_importem()))
    else:
        Aplikacja().mainloop()
