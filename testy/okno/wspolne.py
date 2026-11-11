"""Wspólne dla skryptów okna (testy/okno): Nutka uruchomiona z kodu, ustawienia w pliku tymczasowym, zrzut okna.

Skrypty okna otwierają prawdziwe okno Nutki (i czasem sieć), więc nie są częścią `unittest discover`
(nazwy nie zaczynają się od „test”, folder nie jest pakietem). Uruchamiać z katalogu projektu interpreterem
z build\\venv, np.:  build\\venv\\Scripts\\python testy\\okno\\zrzuty_docs.py pl

Zrzut = PrintWindow samego okna Nutki (nie ekranu - nie złapie innych okien użytkownika).
"""

import ctypes
import json
import os
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WYNIKI = REPO / "build" / "okno"  # zrzuty z testów (build\ jest poza gitem)
# ścieżki na zrzutach: nigdy prawdziwa nazwa konta Windows; podfolder jak domyślny w danym języku (Pobrane / Nutka)
FOLDERY = {"pl": (r"C:\Users\Ty\Music\Pobrane", r"C:\Users\Ty\Videos\Pobrane"),
           "en": (r"C:\Users\You\Music\Nutka", r"C:\Users\You\Videos\Nutka")}


def przygotuj(jezyk: str = "pl", ustawienia: dict | None = None):
    """Język i ustawienia (plik tymczasowy zamiast %LOCALAPPDATA%\\Nutka) PRZED importem app; zwraca moduł app.
    Wypisywanie w UTF-8 (polskie znaki i „✔” na konsoli cp1250)."""
    muzyka, filmy = FOLDERY.get(jezyk, FOLDERY["pl"])
    os.environ["NUTKA_JEZYK"] = jezyk
    for strumien in (sys.stdout, sys.stderr):
        try:
            strumien.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.path.insert(0, str(REPO))
    os.chdir(REPO)
    import aktualizacja_programu

    plik = Path(tempfile.mkdtemp(prefix="nutka-okno-")) / "ustawienia.json"
    plik.write_text(json.dumps(ustawienia if ustawienia is not None else {"folder": muzyka, "folder_wideo": filmy}),
                    encoding="utf-8")
    aktualizacja_programu.USTAWIENIA = plik
    WYNIKI.mkdir(parents=True, exist_ok=True)
    import app
    return app


def ustawienia_testowe() -> dict:
    import aktualizacja_programu
    return json.loads(Path(aktualizacja_programu.USTAWIENIA).read_text(encoding="utf-8"))


class Sprawdzenia:
    """Lista „OK / BŁĄD” z podsumowaniem i kodem wyjścia."""

    def __init__(self):
        self.wyniki = []

    def __call__(self, nazwa: str, warunek, szczegoly: str = ""):
        self.wyniki.append(bool(warunek))
        print(("OK   " if warunek else "BŁĄD ") + nazwa + (f"  ({szczegoly})" if szczegoly else ""), flush=True)

    def koniec(self) -> int:
        print(f"\n{sum(self.wyniki)}/{len(self.wyniki)} OK")
        return 0 if self.wyniki and all(self.wyniki) else 1


def zrzut(widget, plik: Path, przytnij: tuple | None = None):
    """PrintWindow okna, w którym siedzi widget (okno główne albo okienko) -> PNG; przytnij = (x1, y1, x2, y2)."""
    u32 = ctypes.windll.user32
    return zrzut_okna(u32.GetParent(widget.winfo_id()) or widget.winfo_id(), plik, przytnij)


def zrzut_okna(hwnd: int, plik: Path, przytnij: tuple | None = None):
    """PrintWindow okna o danym uchwycie (np. okno zbudowanego Nutka.exe znalezione po PID) -> PNG."""
    from PIL import Image
    u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
    r = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 2)  # 2 = PW_RENDERFULLCONTENT (też treść rysowana przez DWM)

    class BMI(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]
    bmi = BMI(ctypes.sizeof(BMI), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    bufor = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, bufor, ctypes.byref(bmi), 0)
    obraz = Image.frombuffer("RGB", (w, h), bufor, "raw", "BGRX", 0, 1)
    (obraz.crop(przytnij) if przytnij else obraz).save(plik)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    return plik
