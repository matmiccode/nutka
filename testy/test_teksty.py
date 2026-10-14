"""Dwa języki (teksty.py): każdy t("…") z kodu ma tłumaczenie, znaczniki {n} zgodne, przełączanie języka."""

import ast
import re
import unittest
from pathlib import Path

import teksty
from teksty import EN, t

KORZEN = Path(__file__).resolve().parent.parent
MODULY = ("app.py", "spotify_lista.py", "aktualizacja_programu.py", "aktualizacje.py")


def _literaly(wezel: ast.expr) -> list[str | None]:
    """Teksty, jakie może dać argument t(): literał albo `"a" if x else "b"`; None = nie da się odczytać z kodu."""
    if isinstance(wezel, ast.Constant) and isinstance(wezel.value, str):
        return [wezel.value]
    if isinstance(wezel, ast.IfExp):
        return _literaly(wezel.body) + _literaly(wezel.orelse)
    return [None]


def wywolania_t(plik: Path) -> list[tuple[int, str | None]]:
    """(linia, tekst) dla każdego t(...) w pliku; tekst None = argument nie jest literałem."""
    znalezione = []
    for wezel in ast.walk(ast.parse(plik.read_text(encoding="utf-8"))):
        if not (isinstance(wezel, ast.Call) and wezel.args):
            continue
        f = wezel.func
        if (isinstance(f, ast.Name) and f.id == "t") or (isinstance(f, ast.Attribute) and f.attr == "t"):
            znalezione += [(wezel.lineno, tekst) for tekst in _literaly(wezel.args[0])]
    return znalezione


class Slownik(unittest.TestCase):
    def test_kazdy_tekst_z_kodu_ma_tlumaczenie(self):
        brak = []
        for nazwa in MODULY:
            for linia, tekst in wywolania_t(KORZEN / nazwa):
                if tekst is None:
                    brak.append(f"{nazwa}:{linia}: t() bez literału - nie da się sprawdzić")
                elif tekst not in EN:
                    brak.append(f"{nazwa}:{linia}: brak w EN: {tekst!r}")
        self.assertEqual(brak, [], "\n" + "\n".join(brak))

    def test_znaczniki_formatowania(self):
        wzor = re.compile(r"\{[^{}]*\}")
        for pl, en in EN.items():
            with self.subTest(pl=pl):
                self.assertEqual(set(wzor.findall(pl)), set(wzor.findall(en)))
                self.assertTrue(en.strip(), "puste tłumaczenie")
                self.assertEqual(pl.endswith("\n"), en.endswith("\n"))


class Przelaczanie(unittest.TestCase):
    def setUp(self):
        self._jezyk = teksty.jezyk()

    def tearDown(self):
        teksty.ustaw(self._jezyk)

    def test_t(self):
        teksty.ustaw("en")
        self.assertEqual(teksty.jezyk(), "en")
        self.assertEqual(t("Szukaj"), "Search")
        self.assertEqual(t("tego nie ma w słowniku"), "tego nie ma w słowniku")  # lepsze niż pusty napis
        teksty.ustaw("pl")
        self.assertEqual(t("Szukaj"), "Szukaj")

    def test_nieznany_jezyk_to_systemowy(self):
        for zly in ("xx", "", None, "EN"):
            with self.subTest(zly=zly):
                teksty.ustaw(zly)
                self.assertEqual(teksty.jezyk(), teksty.jezyk_systemu())
                self.assertIn(teksty.jezyk(), teksty.JEZYKI)

    def test_formatowanie_po_tlumaczeniu(self):
        teksty.ustaw("en")
        self.assertEqual(t("Pobrano {n} z {m}.").format(n=1, m=2), "Downloaded 1 of 2.")
