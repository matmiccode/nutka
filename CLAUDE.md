# Nutka

Darmowa aplikacja okienkowa (CustomTkinter) na Windows: wyszukujesz albo wklejasz link z YouTube lub Spotify, dostajesz mp3.
Publiczne repo GitHub `matmiccode/nutka` (MIT) z wydaniami do pobrania – część katalogu darmowych apek MATCODE.
Podpis autora: **MATCODE** – bez imienia i nazwiska (świadoma decyzja przy publicznym repo; nigdzie go nie wpisywać).
**Produkt to wyłącznie exe z instalatora.** `python app.py` z `build\venv` służy tylko do szybkich testów
(bez cichych aktualizacji i bez sprawdzania wersji).

## Moduły
- `app.py` – okno i cała logika UI. Długie operacje w wątkach, do UI tylko przez `queue` jako `(rodzaj, wartość)` obsługiwane w `_odbierz_logi`.
  - `WERSJA` = jedyne źródło wersji (czyta ją `zbuduj.ps1`), `REPO_GITHUB`, `BUYCOFFEE_URL` (= https://buycoffee.to/matcode; pusty = przycisk „Postaw kawę autorowi / MATCODE” w prawym górnym rogu nagłówka ukryty; `_przycisk_kawy()`). Zostajemy przy buycoffee.to (decyzja użytkownika).
- `spotify_lista.py` – Spotify → `Lista`/`Utwor` przez **spotapi** (publiczne API web playera, bez kluczy; ~5 s/strona 343 utw.),
  `dopasuj()` w YouTube Music (ytmusicapi: najpierw „songs” ±7 s, potem „videos” ±15 s; tytuł/wykonawca znormalizowane),
  `sciezka_pliku()` (stała nazwa = synchronizacja: istniejący plik = „masz już”), `otaguj()` (mutagen: tagi + okładka ze Spotify).
  **spotDL usunięty**: jego współdzielone klucze API Spotify są dławione (album 10 utw. = 2 min).
- `aktualizacje.py` – ciche aktualizacje lekkich pakietów (yt-dlp nightly, yt-dlp-ejs, ytmusicapi, spotapi) z PyPI.
- `aktualizacja_programu.py` – nowa wersja programu z GitHub Releases: okno z „Co nowego” (= sekcja CHANGELOG), pobranie
  `Nutka-Setup.exe`, SHA256 z pola `digest` assetu, uruchomienie `/SILENT /AKTUALIZACJA=1` (instalator sam odpala nową wersję).
  „Pomiń tę wersję” → `%LOCALAPPDATA%\Nutka\ustawienia.json`. Klik w wersję w stopce = ręczne sprawdzenie.
  Test bez publikowania: `NUTKA_TEST_WYDANIE=<ścieżka do JSON w formacie api.github.com>` (asset `browser_download_url` może być ścieżką lokalną).

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
- Przycisk kawy = obrazek z Pillow (`_przycisk_kawy()`, filiżanka `ikona_kawy()`) rysowany na wycinku gradientu spod pigułki – zaokrąglone rogi CTk mają jeden kolor tła i na gradiencie wychodziły kanciaste.
- Tabela to `ttk.Treeview` (styl „Nutka.Treeview”, motyw `clam`) z 6 kolumnami. Wiersze tylko przez `_wstaw_wiersz()` (6 wartości – ukryte kolumny też liczą się do kolejności!),
  czyszczenie `_wyczysc_tabele()`, status `_ustaw_status()` („✗ …” = tag `blad`). Pełne teksty w `_pelne_teksty`, w tabeli skrócone do „…” (`_skroc_wiersze()`) – nie czytać ich z Treeview.
  Szerokości rozdziela `_dopasuj_kolumny()` (× `_skala` DPI) – wbudowany `stretch` po zmianie `displaycolumns` zostawiał kolumny za krawędzią.
  Zaznaczenie = `WYBRANY` (stonowana malina), róż `AKCENT` zostaje dla głównych przycisków. Nagłówki kolumn zwykłą wielkością liter. Pusta tabela = `_pokaz_pusta(tytuł, opis)`.
- Wolne miejsce w pionie dostaje tylko tabela (log ma stałą wysokość).
- CTk: tekst przycisku przez `.cget("text")`, nie `["text"]`; pole z `textvariable` nie pokazuje placeholdera.
- Pasek tytułu: `DWMWA_CAPTION_COLOR` = `TLO`. Emoji na przyciskach renderują się źle – tylko tekst/▶/■.

## Instalator i wydania
- `zbuduj.ps1` → `build\venv` (świeże pakiety, yt-dlp nightly) → ffmpeg **gpl-shared** z BtbN + `deno.exe` z pip do `narzedzia\` → PyInstaller **onedir** `--windowed` → Inno Setup (`instalator.iss`, per-user, polski) → `dist\Nutka-Setup.exe` (~125 MB).
  - Sam build niczego nie publikuje. **`zbuduj.ps1 -Wydanie`** = `gh release create vX.Y.Z` (instalator + `dist\Nutka-instrukcja.pdf`, opis = sekcja `## [X.Y.Z]` z CHANGELOG.md) + kopia na Dysk Google. Wymaga czystego, wypchniętego repo.
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
- Dodatkowo folder użytkowników na Dysku Google: ID TYLKO w lokalnym `publikacja.local.json` (poza gitem). Nigdy nie wpisywać do repo ID folderu ani nazwisk osób trzecich.
  Samo kopiowanie: `zbuduj.ps1 -TylkoPublikacja` (Dysk Google na komputerze musi działać, dysk G:).
- Instrukcja użytkownika = Claude Doc https://claude.ai/code/artifact/ba388908-1322-4f05-a544-aa58c9e38964 (tab `3e14ba65-02ab`).
  Po zmianie obsługi: popraw doc → eksport PDF A4 → `dist\Nutka-instrukcja.pdf` (idzie do wydania i na Dysk).

## Licencje
- Kod: MIT (`LICENSE`). Instalator zawiera GPL (spotapi, mutagen, FFmpeg) – `THIRD-PARTY.md`; kod jest jawny, więc OK.
- **Nie** odszyfrowujemy niczego ze Spotify (DRM) – tylko dane utworów + dźwięk z YouTube.

## Konwencje
- Kod, komentarze i UI po polsku. Język odpowiedzi: polski.
