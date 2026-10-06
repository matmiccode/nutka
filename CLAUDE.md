# Nutka

Darmowa aplikacja okienkowa (CustomTkinter) na Windows: wyszukujesz albo wklejasz link z YouTube lub Spotify, dostajesz mp3.
Repo GitHub `matmiccode/nutka` (MIT; na razie PRYWATNE – upublicznimy, gdy wersja będzie gotowa dla świata) z wydaniami do pobrania – część katalogu darmowych apek MATCODE.
Podpis autora: **MATCODE** – bez imienia i nazwiska (świadoma decyzja przy publicznym repo; nigdzie go nie wpisywać).
**Produkt to wyłącznie exe z instalatora.** `python app.py` z `build\venv` służy tylko do szybkich testów
(bez cichych aktualizacji i bez sprawdzania wersji).

## Moduły
- `app.py` – okno i cała logika UI. Długie operacje w wątkach, do UI tylko przez `queue` jako `(rodzaj, wartość)` obsługiwane w `_odbierz_logi`.
  - `WERSJA` = jedyne źródło wersji (czyta ją `zbuduj.ps1`), `REPO_GITHUB`, `BUYCOFFEE_URL` (= https://buycoffee.to/matcode; pusty = przycisk „Postaw kawę autorowi / MATCODE” w prawym górnym rogu nagłówka ukryty; `_przyciski_naglowka()`). Zostajemy przy buycoffee.to (decyzja użytkownika).
- `spotify_lista.py` – Spotify → `Lista`/`Utwor` przez **spotapi** (publiczne API web playera, bez kluczy; ~5 s/strona 343 utw.),
  `dopasuj()` w YouTube Music (ytmusicapi: najpierw „songs” ±7 s, potem „videos” ±15 s; tytuł/wykonawca znormalizowane),
  `sciezka_pliku()` (stała nazwa = synchronizacja: istniejący plik = „masz już”), `otaguj()` (mutagen: tagi + okładka ze Spotify).
  **spotDL usunięty**: jego współdzielone klucze API Spotify są dławione (album 10 utw. = 2 min).
- `aktualizacje.py` – ciche aktualizacje lekkich pakietów (yt-dlp nightly, yt-dlp-ejs, ytmusicapi, spotapi) z PyPI.
- `aktualizacja_programu.py` – nowa wersja programu z GitHub Releases: okno z „Co nowego” (= sekcja CHANGELOG), **podpis**
  `Nutka-Setup.podpis.json` (Ed25519 nad `nazwa\nwersja\nsha256`, `sprawdz_podpis()` kluczem `KLUCZ_PUBLICZNY`), pobranie
  `Nutka-Setup.exe`, SHA256 = ta podpisana (digest GitHuba tylko krzyżowo), uruchomienie `/SILENT /AKTUALIZACJA=1`.
  Wydanie bez podpisu nie jest proponowane. „Pomiń tę wersję” → `%LOCALAPPDATA%\Nutka\ustawienia.json`. Link „Sprawdź aktualizacje” w stopce = ręczne sprawdzenie.
  Test bez publikowania: `NUTKA_TEST_WYDANIE=<ścieżka do JSON w formacie api.github.com>` (assety `browser_download_url` mogą być ścieżkami lokalnymi; tylko wtedy).
- `podpis_wydania.py` – `nowy-klucz` (raz; wpisuje klucz publiczny do modułu wyżej), `podpisz` (robi `zbuduj.ps1 -Wydanie`), `sprawdz`.
  Klucz prywatny: `%APPDATA%\MATCODE\nutka-klucz-wydania.pem` (albo `NUTKA_KLUCZ_WYDANIA`) – **POZA REPO, użytkownik ma mieć kopię**;
  zgubiony klucz = zainstalowane Nutki nie przyjmą żadnego wydania (ręczna reinstalacja). Wymaga pakietu `cryptography` (requirements.txt).

## Jak działa
- **YouTube** → `yt-dlp` (`-x --audio-format mp3 --audio-quality 0`, okładka + metadane), konwersja przez ffmpeg.
  - Odpalany z `-q` + własnymi znacznikami (`UTWOR`/`POSTEP`/`PLIK` przez `--print`/`--progress-template`), które `_przetworz_linie` zamienia na krótki log i pasek postępu.
  - Link z `&list=` (miks) = jeden utwór (`--no-playlist`); tylko `youtube.com/playlist?list=` / `music.youtube.com/browse/` pobiera całość do podfolderu.
- **Spotify (utwór/album/playlista)** → zawsze **tryb listy**: tabela z ☑ i STATUS (`_pokaz_kolumny`), „Pobierz zaznaczone (N)”,
  w trakcie przycisk = „Zatrzymaj”. Pobieranie: `ThreadPoolExecutor(ROWNOLEGLE_POBIERANIA=3)`, na utwór: dopasuj → `komenda_utworu()` (yt-dlp do dokładnej ścieżki) → `otaguj()`.
  Po końcu udane się odznaczają, nieudane zostają zaznaczone (= „spróbuj ponownie”). Prywatnych playlist i „Polubionych” spotapi nie widzi.
- **Wyszukiwarka** → `ytmusicapi` (`location="PL"`; `language` nie obsługuje polskiego), klient na wątek (`klient_yt_music()`). Albumy przez `playlistId` (OLAK5uy_...).
- **Odsłuch** → `yt-dlp --print title --print urls -f bestaudio`, `ffplay -nodisp`. Album YouTube po kolei (adres następnego z wyprzedzeniem);
  w trybie listy Spotify: odsłuch zaznaczonego wiersza (dopasowanie w tle). „Następny” = kill ffplay, Stop = `odsluch_nr += 1`.

## Wygląd
- CustomTkinter, ciemny motyw w kolorach ikony – paleta w stałych na górze `app.py` (`TLO`, `KARTA`, `POLE`, `AKCENT`…). Nowe kontrolki: `_przycisk()` / `_pole()`.
- Nagłówek = `naglowek.png` (gradient + nutka + nazwa, 2x pod DPI, szerszy niż okno; ramka ma kolor `FIOLET`). Ekran startowy = `splash.png`. Oba wygenerowane Pillow (Segoe UI) – przy zmianie nazwy przerysować.
- Prawy górny róg = `_przyciski_naglowka()`: pigułki z `_pigulka()` – obrazek Pillow na wycinku gradientu spod pigułki (zaokrąglone rogi CTk mają jeden kolor tła i na gradiencie wychodziły kanciaste).
  Obie szklane (biała pigułka przyćmiewała „Szukaj”): „Postaw kawę autorowi / MATCODE” (filiżanka `ikona_kawy()`) + „Instrukcja” → `_otworz_instrukcje()` = `instrukcja\instrukcja.html` obok exe w przeglądarce (fallback `STRONA_INSTRUKCJI`).
- Jeden róż `AKCENT` na ekranie = tylko akcje (Szukaj, Pobierz, Stop); zaznaczenia (segment Utwory/Albumy, wiersz tabeli) w `WYBRANY`.
  Treść pod nagłówkiem ma najwyżej `MAKS_SZEROKOSC` (1280 px, `_ogranicz_szerokosc()` – waga tylko na kolumnie treści, bo grid kurczy wyłącznie kolumny z wagą); minimalne okno 900x660.
  Pasek postępu w spoczynku ma kolor tła (`_schowaj_postep()`), obok napis z procentem albo „3/12”; „Następny ›” tylko podczas odsłuchu (`_pokaz_odsluch()`).
- Tabela to `ttk.Treeview` (styl „Nutka.Treeview”, motyw `clam`) z 6 kolumnami. Wiersze tylko przez `_wstaw_wiersz()` (6 wartości – ukryte kolumny też liczą się do kolejności!),
  czyszczenie `_wyczysc_tabele()`, status `_ustaw_status()` („✗ …” = tag `blad`). Pełne teksty w `_pelne_teksty`, w tabeli skrócone do „…” (`_skroc_wiersze()`) – nie czytać ich z Treeview.
  Szerokości rozdziela `_dopasuj_kolumny()` (× `_skala` DPI) – wbudowany `stretch` po zmianie `displaycolumns` zostawiał kolumny za krawędzią.
  Zaznaczenie = `WYBRANY` (stonowana malina). Nagłówki kolumn zwykłą wielkością liter. Pusta tabela = `_pokaz_pusta(tytuł, opis)` (zasłania całą kartę, z nagłówkami). Opis nad listą skraca `_ustaw_opis_listy()` (najpierw nazwę w cudzysłowie).
- Wolne miejsce w pionie dostaje tylko tabela (log ma stałą wysokość).
- CTk: tekst przycisku przez `.cget("text")`, nie `["text"]`; pole z `textvariable` nie pokazuje placeholdera.
- Pasek tytułu: `DWMWA_CAPTION_COLOR` = `TLO`. Emoji na przyciskach renderują się źle – tylko tekst/▶/■.

## Instalator i wydania
- `zbuduj.ps1` → `build\venv` (świeże pakiety, yt-dlp nightly) → ffmpeg **gpl-shared** z BtbN + `deno.exe` z pip do `narzedzia\` → PyInstaller **onedir** `--windowed` → Inno Setup (`instalator.iss`, per-user, polski) → `dist\Nutka-Setup.exe` (~115 MB).
  - Sam build niczego nie publikuje. **`zbuduj.ps1 -Wydanie`** = podpis (`podpis_wydania.py podpisz`) + `gh release create vX.Y.Z`
    (`Nutka-Setup.exe` + `Nutka-Setup.podpis.json`, opis = sekcja `## [X.Y.Z]` z CHANGELOG.md). Wymaga czystego, wypchniętego repo i klucza prywatnego.
  - Build kopiuje `docs\instrukcja.html` + zrzuty + ikony do `build\dist\Nutka\instrukcja\` (instalator bierze cały katalog).
  - Procedura wydania: podbij `WERSJA` w app.py → sekcja w CHANGELOG.md (pisana dla zwykłego użytkownika – to jest „Co nowego” w programie) → commit/push → `zbuduj.ps1 -Wydanie`.
- W exe nie ma `python -m`, więc `narzedzie()` woła sam exe z `--yt-dlp`, a `uruchom_narzedzie()` odpala `yt_dlp.main()`.
- PyInstaller ignoruje `PYTHONUTF8` → `wyjscie_utf8()` w procesach potomnych. `ZASOBY` = `sys._MEIPASS` (`__file__` tam NIE wskazuje).
- Splash psuje ikonę okna → `_ustaw_ikone()` jeszcze raz po `zamknij_ekran_startowy()`; procesy potomne: `PYINSTALLER_SUPPRESS_SPLASH_SCREEN=1`.
- Instalator przy aktualizacji kasuje `_internal` i `%LOCALAPPDATA%\Nutka\pakiety` (stare ciche pakiety przykryłyby nowsze z exe); `[Run]` z `Check: CzyAktualizacja` odpala program po `/AKTUALIZACJA=1`.
- `--autotest` – raport: narzędzia, yt-dlp, wyszukiwanie, Spotify, najnowsze wydanie na GitHubie. `--wersje` – test kandydata w aktualizacje.py.
- Testować z okrojonym PATH przez `subprocess` z Pythona (PowerShell nie łapie wyjścia exe okienkowych); zrzuty okna tylko przez PrintWindow (nie ImageGrab ekranu – łapie prywatne okna użytkownika).
- `zbuduj.ps1` / `instalator.iss` muszą mieć **UTF-8 z BOM**; w PowerShellu NIE używać „” w stringach (PS traktuje je jak `"`).

## Publikacja dla użytkowników
- Użytkownicy to zwykli ludzie (nie firma) – tak pisać instrukcje, komunikaty i CHANGELOG.
- Wydania: GitHub Releases (repo publiczne; `releases/latest/download/Nutka-Setup.exe` = stały link w README).
- **Nie kopiujemy już wydań na Dysk Google** (decyzja użytkownika 2026-10-06) – jedyne źródło to GitHub Releases. Nigdy nie wpisywać do repo nazwisk osób trzecich.
- Instrukcja użytkownika = **`docs/instrukcja.html`** (jeden plik HTML, te same tokeny CSS co `docs/index.html`, zrzuty z `docs/`).
  Po zmianie obsługi edytuj HTML i wydaj nową wersję – trafia do instalatora (`instrukcja\` obok exe) i na Pages pod `/nutka/instrukcja.html`.
  PDF i Claude Doc (decyzja 2026-10-06) **wycofane** – nie generować, nie dołączać do wydań.
- Strona programu = `docs/index.html` (GitHub Pages z `master` /docs, jeden plik, zrzuty z `docs/`). Włączyć dopiero po upublicznieniu repo: Settings → Pages.
- Zrzuty do README/instrukcji/strony (`docs/zrzut-*.png`): `python` + PrintWindow na danych testowych, folder ustawiony na `C:\Users\Ty\Music\Pobrane` (nigdy prawdziwa nazwa użytkownika).
  Skrypt `zrzuty_docs.py` w scratchpadzie Claude (kroki jako łańcuch `after`, bo `update()` w kroku mieszał kolejność absolutnych `after`).

## Licencje
- Kod: MIT (`LICENSE`). Instalator zawiera GPL (spotapi, mutagen, FFmpeg) – `THIRD-PARTY.md`; kod jest jawny, więc OK.
- **Nie** odszyfrowujemy niczego ze Spotify (DRM) – tylko dane utworów + dźwięk z YouTube.

## Bezpieczeństwo (nie psuć przy zmianach)
- Wklejony tekst = argument yt-dlp: `rozpoznaj_zrodlo()` uznaje link tylko po http(s) i hoście z `HOSTY_YOUTUBE`/`HOSTY_SPOTIFY` (nie po podciągu);
  każde wywołanie yt-dlp ma `--ignore-config` i `--` przed adresem, żeby tekst zaczynający się od „-” nie stał się opcją.
- Nazwy z internetu → `bezpieczna_nazwa()`: znaki zabronione, kropki/spacje z obu końców (Win32 je ignoruje, więc `.. ` = katalog nadrzędny),
  nazwy urządzeń CON/NUL/COM1… → `_CON`; `sciezka_pliku()` dodatkowo sprawdza `is_relative_to(folder)`. yt-dlp sanityzuje swoje szablony sam.
  Okładka tylko https z `*.scdn.co`/`*.spotifycdn.com`.
- Aktualizacja programu: instalator tylko z `https://github.com/<REPO_GITHUB>/releases/download/`, brak `digest` = błąd (fail-closed);
  lokalna ścieżka assetu działa tylko z ustawionym `NUTKA_TEST_WYDANIE`. Pakiety z PyPI tylko z `https://files.pythonhosted.org/` + SHA256 z JSON PyPI.
- Wydania programu podpisane Ed25519 (`podpis_wydania.py`, klucz publiczny w `aktualizacja_programu.py`) – przejęcie konta GitHub nie wystarczy
  do podsunięcia instalatora. Pakiety z PyPI nadal ufają TLS + kontom autorów (jak `pip`). Konto GitHub ma 2FA; po upublicznieniu: ochrona tagów,
  Dependabot, secret scanning, CodeQL. `SECURITY.md` opisuje zgłaszanie luk (GitHub private reporting, bez maila).
- Przegląd 2026-10-06 (`/code-review` + agent bezpieczeństwa): bez `shell=True`, wheele przez bezpieczny `zipfile`, stan i pliki tymczasowe per-user,
  hooki testowe (`NUTKA_TEST_WYDANIE`, `MUZYKA_PAKIETY_TEST`, `--yt-dlp/--autotest/--wersje`) tylko z env/argv.

## Konwencje
- Kod, komentarze i UI po polsku. Język odpowiedzi: polski.
