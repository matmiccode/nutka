"""Podpis wydania Nutki (MATCODE) - klucz Ed25519 niezależny od GitHuba i PyPI.

Program (aktualizacja_programu.py) instaluje nową wersję tylko wtedy, gdy wydanie ma plik Nutka-Setup.podpis.json,
a podpis w nim zgadza się z kluczem publicznym wkompilowanym w program (KLUCZ_PUBLICZNY). Przejęcie konta GitHub
nie wystarczy więc, żeby podsunąć użytkownikom obcy instalator - potrzebny jest klucz prywatny, który leży tylko
na komputerze autora, poza repozytorium.

  python podpis_wydania.py nowy-klucz
      tworzy parę kluczy: prywatny -> %APPDATA%\\MATCODE\\nutka-klucz-wydania.pem (albo NUTKA_KLUCZ_WYDANIA),
      publiczny -> wpisuje do aktualizacja_programu.py (KLUCZ_PUBLICZNY). Istniejącego klucza nie nadpisuje.
  python podpis_wydania.py podpisz dist\\Nutka-Setup.exe 1.3.0
      -> dist\\Nutka-Setup.podpis.json (robi to zbuduj.ps1 -Wydanie)
  python podpis_wydania.py sprawdz dist\\Nutka-Setup.exe dist\\Nutka-Setup.podpis.json 1.3.0
      sprawdza plik tak, jak zrobi to program u użytkownika

ZRÓB KOPIĘ KLUCZA PRYWATNEGO (np. w menedżerze haseł). Bez niego nie wydasz wersji, którą zainstalowane Nutki
przyjmą - z nowym kluczem użytkownicy musieliby zainstalować program ręcznie.
Podpisywana jest krótka wiadomość (nazwa pliku, wersja, SHA256 instalatora), więc podpis wiąże plik z wersją:
stare, podpisane wydanie nie da się ponownie opublikować jako „nowsze”.
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import aktualizacja_programu as ap

KLUCZ = Path(os.environ.get("NUTKA_KLUCZ_WYDANIA") or Path(os.environ.get("APPDATA", Path.home())) / "MATCODE" / "nutka-klucz-wydania.pem")


def sha256_pliku(plik: Path) -> str:
    skrot = hashlib.sha256()
    with plik.open("rb") as f:
        while kawalek := f.read(1 << 20):
            skrot.update(kawalek)
    return skrot.hexdigest()


def nowy_klucz():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if KLUCZ.exists():
        sys.exit(f"Klucz już istnieje: {KLUCZ} - nie nadpisuję (zainstalowane Nutki ufają tylko jemu).")
    klucz = Ed25519PrivateKey.generate()
    KLUCZ.parent.mkdir(parents=True, exist_ok=True)
    KLUCZ.write_bytes(klucz.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
    publiczny = klucz.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    modul = Path(__file__).with_name("aktualizacja_programu.py")
    tekst, ile = re.subn(r'^KLUCZ_PUBLICZNY = "[0-9a-f]*"', f'KLUCZ_PUBLICZNY = "{publiczny}"',
                         modul.read_text(encoding="utf-8"), flags=re.M)
    if ile != 1:
        sys.exit("Nie znalazłem linii KLUCZ_PUBLICZNY = \"...\" w aktualizacja_programu.py")
    modul.write_text(tekst, encoding="utf-8")
    print(f"Klucz prywatny: {KLUCZ}  <- ZRÓB KOPIĘ\nKlucz publiczny wpisany do aktualizacja_programu.py: {publiczny}")


def podpisz(plik: Path, wersja: str) -> Path:
    from cryptography.hazmat.primitives import serialization

    if plik.name != ap.NAZWA_INSTALATORA:
        sys.exit(f"Podpisuję tylko {ap.NAZWA_INSTALATORA} (dostałem {plik.name})")
    if not KLUCZ.exists():
        sys.exit(f"Brak klucza prywatnego {KLUCZ} - przywróć go z kopii (nowy klucz = ręczna reinstalacja u użytkowników).")
    klucz = serialization.load_pem_private_key(KLUCZ.read_bytes(), password=None)
    sha = sha256_pliku(plik)
    dane = {"format": ap.FORMAT_PODPISU, "plik": plik.name, "wersja": wersja, "sha256": sha,
            "podpis": klucz.sign(ap.wiadomosc_podpisu(plik.name, wersja, sha)).hex()}
    ap.sprawdz_podpis(dane, wersja)  # od razu kontrola kluczem publicznym z programu - musi pasować do prywatnego
    wyjscie = plik.with_name(ap.NAZWA_PODPISU)
    wyjscie.write_text(json.dumps(dane, indent=1), encoding="utf-8")
    print(f"Podpisano {plik.name} {wersja} (SHA256 {sha[:16]}…) -> {wyjscie}")
    return wyjscie


def sprawdz(plik: Path, plik_podpisu: Path, wersja: str):
    dane = json.loads(plik_podpisu.read_text(encoding="utf-8"))
    oczekiwana = ap.sprawdz_podpis(dane, wersja)
    if sha256_pliku(plik) != oczekiwana:
        sys.exit(f"SHA256 pliku {plik.name} nie zgadza się z podpisaną.")
    print(f"OK: {plik.name} {wersja} ma prawidłowy podpis autora.")


if __name__ == "__main__":
    polecenie, argumenty = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if polecenie == "nowy-klucz" and not argumenty:
        nowy_klucz()
    elif polecenie == "podpisz" and len(argumenty) == 2:
        podpisz(Path(argumenty[0]), argumenty[1])
    elif polecenie == "sprawdz" and len(argumenty) == 3:
        sprawdz(Path(argumenty[0]), Path(argumenty[1]), argumenty[2])
    else:
        sys.exit(__doc__)
