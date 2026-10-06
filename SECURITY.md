# Bezpieczeństwo / Security

## Zgłaszanie luk (PL)

Jeśli znajdziesz w Nutce lukę bezpieczeństwa, **nie opisuj jej w publicznym zgłoszeniu**.
Użyj prywatnego zgłoszenia na GitHubie: zakładka **Security → Report a vulnerability** w tym repozytorium.
Nutka to projekt hobbystyczny jednej osoby – odpowiadam najszybciej, jak mogę, zwykle w ciągu kilku dni.

Wspierana jest wyłącznie **najnowsza wersja** (program sam proponuje aktualizację).

## Jak Nutka chroni użytkowników

- **Podpisane wydania.** Każde wydanie ma plik `Nutka-Setup.podpis.json` z podpisem Ed25519 kluczem autora,
  który leży poza GitHubem. Program instaluje nową wersję tylko wtedy, gdy podpis, wersja i suma SHA256 instalatora
  się zgadzają. Samo przejęcie konta GitHub nie wystarczy, żeby podsunąć użytkownikom obcy instalator.
- **Tylko oficjalne źródła.** Instalator wyłącznie z `https://github.com/matmiccode/nutka/releases/download/…`,
  paczki silnika (yt-dlp, ytmusicapi, spotapi) wyłącznie z `https://files.pythonhosted.org/` z sumą SHA256 z PyPI.
- **Wklejony tekst nie jest poleceniem.** Link jest uznawany tylko po schemacie i hoście (YouTube, Spotify),
  a do yt-dlp trafia po separatorze `--`, więc nie może zostać opcją programu.
- **Nazwy plików z internetu** są czyszczone (znaki zabronione, kropki i spacje na końcach, nazwy urządzeń Windows),
  a ścieżka zapisu jest sprawdzana, czy leży w wybranym folderze.
- Instalacja per użytkownik, bez uprawnień administratora; żadnych kont, kluczy API ani telemetrii.

Znane ograniczenie: paczki silnika pochodzą z PyPI i są ufane na podstawie TLS oraz kont ich autorów
(jak przy `pip install`). Instalator nie ma płatnego podpisu Authenticode, stąd ostrzeżenie SmartScreen.

## Reporting a vulnerability (EN)

Please do not open a public issue for security problems. Use GitHub's private reporting:
**Security → Report a vulnerability** in this repository. Nutka is a one-person hobby project; expect a reply
within a few days. Only the latest release is supported.

Release integrity: every release ships `Nutka-Setup.podpis.json`, an Ed25519 signature (key held offline by the
author) over the installer's name, version and SHA256. The in-app updater refuses unsigned or mismatched releases,
downloads only from this repository's release URLs, and never passes pasted text to `yt-dlp` as an option.
