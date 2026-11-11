"""Zbudowany program (build\\dist\\Nutka\\Nutka.exe) przed wydaniem. Użycie: build\\venv\\Scripts\\python testy\\okno\\okno_exe.py
Sieć, ok. 1-2 min. LOCALAPPDATA = katalog tymczasowy i okrojony PATH (tylko narzędzia z paczki), więc zainstalowana
Nutka zostaje nietknięta, a test widzi to, co dostanie użytkownik.

 T1 obok exe: LICENSE, THIRD-PARTY.md (z LRCLIB), instrukcja PL i EN z wszystkimi obrazkami z docs/img
 T2 autotest z pobieraniem: kod wyjścia 0 („wszystko działa”)
 T3 okno exe startuje po polsku i po angielsku (zrzuty do build\\okno\\exe-<wersja>-pl|en.png - obejrzeć stopkę, kawę, przełączniki)
"""

import ctypes
import os
import re
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

from wspolne import REPO, WYNIKI, Sprawdzenia, zrzut_okna

for strumien in (sys.stdout, sys.stderr):
    strumien.reconfigure(encoding="utf-8")
EXE = REPO / "build" / "dist" / "Nutka" / "Nutka.exe"
WERSJA = re.search(r'WERSJA = "([\d.]+)"', (REPO / "app.py").read_text(encoding="utf-8"))[1]
DANE = tempfile.mkdtemp(prefix="nutka-exe-dane-")
ENV = {**os.environ, "PATH": r"C:\Windows\System32;C:\Windows", "LOCALAPPDATA": DANE}
WYNIKI.mkdir(parents=True, exist_ok=True)
sprawdz = Sprawdzenia()

# T1 - pliki obok exe
folder = EXE.parent
trzecie = (folder / "THIRD-PARTY.md").read_text(encoding="utf-8").lower() if (folder / "THIRD-PARTY.md").exists() else ""
sprawdz("T1 LICENSE i THIRD-PARTY.md (z LRCLIB)", (folder / "LICENSE").exists() and "lrclib" in trzecie)
for jezyk, docs, inst in (("pl", REPO / "docs" / "img", folder / "instrukcja" / "img"),
                          ("en", REPO / "docs" / "img" / "en", folder / "instrukcja" / "img" / "en")):
    brakuje = sorted(p.name for p in docs.glob("*.png") if not (inst / p.name).exists())
    html = folder / "instrukcja" / ("en/instrukcja.html" if jezyk == "en" else "instrukcja.html")
    sprawdz(f"T1 instrukcja {jezyk} z obrazkami", html.exists() and not brakuje, f"brakuje: {brakuje}" if brakuje else "")

# T2 - autotest jak „Zgłoś problem”, z prawdziwym pobraniem
r = subprocess.run([str(EXE), "--autotest", "--pobierz"], capture_output=True, text=True, encoding="utf-8",
                   errors="replace", env=ENV, timeout=600)
print(r.stdout.strip()[-1800:])
sprawdz("T2 autotest z pobieraniem", r.returncode == 0, f"kod {r.returncode}")


def okno_procesu(pid: int, czekaj_s: int = 40):
    """Widoczne okno „Nutka…” procesu o danym PID (po zniknięciu ekranu startowego)."""
    u32 = ctypes.windll.user32
    koniec = time.time() + czekaj_s
    while time.time() < koniec:
        znalezione = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def zbierz(hwnd, _):
            p = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            dlugosc = u32.GetWindowTextLengthW(hwnd)
            if p.value == pid and u32.IsWindowVisible(hwnd) and dlugosc:
                bufor = ctypes.create_unicode_buffer(dlugosc + 1)
                u32.GetWindowTextW(hwnd, bufor, dlugosc + 1)
                if bufor.value.startswith("Nutka"):
                    znalezione.append(hwnd)
            return True
        u32.EnumWindows(zbierz, 0)
        if znalezione:
            return znalezione[0]
        time.sleep(1)
    return None


# T3 - okno exe w obu językach
for jezyk in ("pl", "en"):
    proces = subprocess.Popen([str(EXE)], env={**ENV, "NUTKA_JEZYK": jezyk})
    try:
        hwnd = okno_procesu(proces.pid)
        time.sleep(4)  # ekran startowy znika, okno się rysuje
        plik = WYNIKI / f"exe-{WERSJA}-{jezyk}.png"
        if hwnd:
            zrzut_okna(hwnd, plik)
        sprawdz(f"T3 okno exe ({jezyk})", hwnd is not None, str(plik) if hwnd else "")
    finally:
        proces.terminate()
        proces.wait(10)
sys.exit(sprawdz.koniec())
