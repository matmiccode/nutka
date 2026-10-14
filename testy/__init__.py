"""Testy jednostkowe Nutki - bez sieci i bez okna.

Uruchomienie z katalogu projektu:  python -m unittest discover -s testy -t . -v
To samo robi GitHub Actions przy każdej zmianie kodu (.github/workflows/testy.yml).
Sprawdzenie, czy YouTube, Spotify i PyPI nadal współpracują z programem, to osobny codzienny czujnik
(.github/workflows/czujnik.yml), który uruchamia `app.py --autotest`.
"""
