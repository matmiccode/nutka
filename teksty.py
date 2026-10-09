"""Teksty interfejsu Nutki w dwóch językach (MATCODE).

Kod i teksty w kodzie zostają po polsku; t("Szukaj") zwraca „Search”, gdy wybrany jest angielski. Tabela EN niżej
to jedyne miejsce z tłumaczeniami - tekst, którego w niej nie ma, zostaje po polsku (lepsze to niż pusty napis).
Teksty ze znacznikami {n} formatuje się po przetłumaczeniu: t("Pobrano {n} z {m}.").format(n=…, m=…).

Język: NUTKA_JEZYK (testy) > „jezyk” w %LOCALAPPDATA%\\Nutka\\ustawienia.json (przełącznik w nagłówku)
> język interfejsu Windows (polski -> pl, każdy inny -> en).
"""

import ctypes
import os

JEZYKI = ("pl", "en")
_jezyk = "pl"


def jezyk_systemu() -> str:
    """pl, gdy Windows mówi po polsku; inaczej en."""
    try:
        return "pl" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x15 else "en"
    except (AttributeError, OSError):
        return "pl"


def ustaw(jezyk: str | None):
    """Pusty/nieznany = język systemu."""
    global _jezyk
    _jezyk = jezyk if jezyk in JEZYKI else jezyk_systemu()


def jezyk() -> str:
    return _jezyk


def t(tekst: str) -> str:
    return EN.get(tekst, tekst) if _jezyk == "en" else tekst


ustaw(os.environ.get("NUTKA_JEZYK"))

EN = {
    # okno, nagłówek
    "muzyka z YouTube i Spotify": "music from YouTube and Spotify",
    "Postaw kawę autorowi": "Buy the author a coffee",
    "Instrukcja": "Guide",
    "Pobrane": "Nutka",  # domyślny podfolder w Muzyce
    # wyszukiwarka
    "Wpisz tytuł lub wykonawcę – albo wklej link z YouTube lub Spotify":
        "Type a title or artist – or paste a YouTube or Spotify link",
    "Utwory": "Songs",
    "Albumy": "Albums",
    "Szukaj": "Search",
    # tabela
    "Tytuł": "Title",
    "Wykonawca": "Artist",
    "Album": "Album",
    "Czas": "Time",
    "Status": "Status",
    "Zamknij listę": "Close list",
    "Odznacz wszystko": "Clear all",
    "Zaznacz wszystko": "Select all",
    "Czego chcesz posłuchać?": "What would you like to hear?",
    "Wpisz tytuł lub wykonawcę i kliknij „Szukaj” – albo wklej link z YouTube lub Spotify.\n"
    "Klik w wynik wybiera utwór, dwuklik od razu go pobiera.":
        "Type a title or artist and click “Search” – or paste a YouTube or Spotify link.\n"
        "Click a result to select it, double-click to download it right away.",
    "Nic nie znaleziono": "Nothing found",
    "Sprawdź pisownię albo wpisz samego wykonawcę.\nSzukasz całej płyty? Przełącz na „Albumy”.":
        "Check the spelling or type just the artist.\nLooking for a whole record? Switch to “Albums”.",
    # link, folder, przyciski
    "Link": "Link",
    "Wklej": "Paste",
    "Zapisz do": "Save to",
    "Wybierz…": "Browse…",
    "Pobierz mp3": "Download mp3",
    "▶  Odsłuchaj": "▶  Listen",
    "■  Stop": "■  Stop",
    "Następny  ›": "Next  ›",
    "Otwórz folder": "Open folder",
    "Pobierz zaznaczone ({n})": "Download selected ({n})",
    "Zatrzymaj": "Stop",
    # stopka
    "Sprawdź aktualizacje": "Check for updates",
    "silnik yt-dlp": "yt-dlp engine",
    # dziennik i komunikaty
    "🔍 Szukam: {fraza}": "🔍 Searching: {fraza}",
    "✖ Wyszukiwanie nie wyszło: {e}": "✖ Search failed: {e}",
    "Najpierw poczekaj na koniec pobierania listy (albo kliknij „Zatrzymaj”).":
        "Wait for the list download to finish first (or click “Stop”).",
    "Trwa pobieranie listy - poczekaj albo kliknij „Zatrzymaj”.": "A list is being downloaded – wait or click “Stop”.",
    "Najpierw zatrzymaj pobieranie listy.": "Stop the list download first.",
    "Spotify": "Spotify",
    "To nie wygląda na link do utworu, albumu ani playlisty Spotify.\nW Spotify: … → Udostępnij → Kopiuj link.":
        "This doesn't look like a link to a Spotify track, album or playlist.\nIn Spotify: … → Share → Copy link.",
    "Wczytuję listę utworów ze Spotify…": "Loading the track list from Spotify…",
    "✖ Nie udało się wczytać listy ze Spotify ({e}). Czy playlista jest publiczna? Prywatnych playlist "
    "i „Polubionych” program nie widzi.":
        "✖ Couldn't load the list from Spotify ({e}). Is the playlist public? Private playlists and "
        "“Liked Songs” are not visible to the app.",
    "Playlista": "Playlist",
    "Utwór": "Track",
    "„": "“",  # cudzysłów otwierający przed nazwą listy (zamykający ” jest wspólny)
    "utw.": "tracks",
    "{n} już masz": "{n} already yours",
    "masz już": "already yours",
    "♫ {opis} Odznacz, czego nie chcesz, i kliknij „Pobierz zaznaczone”.":
        "♫ {opis} Untick what you don't want and click “Download selected”.",
    " – {n} już masz, są odznaczone.": " – {n} already yours, unticked.",
    "Nic nie jest zaznaczone.": "Nothing is selected.",
    "Pobieranie": "Download",
    "w kolejce": "queued",
    "▶ Pobieram {n} utw. z „{nazwa}” (po {k} naraz)…": "▶ Downloading {n} tracks from “{nazwa}” ({k} at a time)…",
    "szukam…": "searching…",
    "brak na YouTube": "not on YouTube",
    "pobieram {p} %": "downloading {p} %",
    "przerwano": "stopped",
    "błąd": "error",
    "zapisuję…": "saving…",
    "pobrano": "done",
    "Zatrzymuję…": "Stopping…",
    "■ Zatrzymano. ": "■ Stopped. ",
    "✔ Gotowe. ": "✔ Done. ",
    "Pobrano {n} z {m}.": "Downloaded {n} of {m}.",
    "Nie udało się {n} – zostały zaznaczone; kliknij „Pobierz zaznaczone”, żeby spróbować jeszcze raz.":
        "{n} failed – they stay ticked; click “Download selected” to try again.",
    # odsłuch
    "Odsłuch": "Listen",
    "Brak ffplay (część ffmpeg) - zainstaluj program ponownie.": "ffplay (part of ffmpeg) is missing – reinstall the app.",
    "Kliknij utwór na liście, który chcesz odsłuchać.": "Click the track on the list you want to hear.",
    "Wybierz utwór z wyników albo wklej link z YouTube.": "Pick a track from the results or paste a YouTube link.",
    "✖ Nie znalazłem „{tytul}” na YouTube Music.": "✖ Couldn't find “{tytul}” on YouTube Music.",
    "✖ Nie da się odtworzyć: {blad}": "✖ Can't play: {blad}",
    "✖ Odsłuch nie działa: {e}": "✖ Playback failed: {e}",
    "pusta playlista": "empty playlist",
    # pobieranie
    "Zły link": "Bad link",
    "Wybierz coś z wyników albo wklej link z YouTube lub Spotify.":
        "Pick something from the results or paste a YouTube or Spotify link.",
    "▶ Start ({zrodlo}): {link}": "▶ Start ({zrodlo}): {link}",
    "✔ Gotowe.": "✔ Done.",
    "✖ Błąd (kod {kod}) - szczegóły wyżej.": "✖ Error (code {kod}) – details above.",
    "✖ Nie udało się uruchomić: {e}": "✖ Couldn't start: {e}",
    "Nieznany link - obsługiwane są YouTube i Spotify.": "Unknown link – YouTube and Spotify are supported.",
    # aktualizacje programu
    "✖ Nie udało się sprawdzić aktualizacji: {e}": "✖ Couldn't check for updates: {e}",
    "✔ Masz najnowszą wersję Nutki ({wersja}).": "✔ You have the latest Nutka ({wersja}).",
    "Sprawdzam, czy jest nowa wersja Nutki…": "Checking for a new Nutka version…",
    "Aktualizacja Nutki": "Nutka update",
    "Dostępna jest nowa wersja Nutki {wersja}": "Nutka {wersja} is available",
    "Masz wersję {wersja}. Aktualizacja zajmie około minuty, Twoje pliki zostają.":
        "You have {wersja}. The update takes about a minute, your files stay where they are.",
    "Co nowego:": "What's new:",
    "Poprawki i ulepszenia.": "Fixes and improvements.",
    "Aktualizacja": "Update",
    "Trwa pobieranie - przerwać je i zaktualizować teraz?": "A download is in progress – stop it and update now?",
    "Pobieram nową wersję…": "Downloading the new version…",
    "Pobieram nową wersję… {p}%": "Downloading the new version… {p}%",
    "Zaktualizuj teraz": "Update now",
    "Przypomnij później": "Remind me later",
    "Pomiń tę wersję": "Skip this version",
    "Nie udało się pobrać aktualizacji:\n{blad}": "Couldn't download the update:\n{blad}",
    "Podpis wydania dotyczy innego pliku lub innej wersji - nie instaluję.":
        "The release signature is for a different file or version – not installing.",
    "Podpis wydania nie zawiera poprawnej sumy SHA256 - nie instaluję.":
        "The release signature has no valid SHA256 checksum – not installing.",
    "Podpis wydania nie zgadza się z kluczem autora - nie instaluję.":
        "The release signature doesn't match the author's key – not installing.",
    "Wydanie {wersja} nie ma podpisu autora ({plik}) - nie proponuję aktualizacji.":
        "Release {wersja} has no author signature ({plik}) – not offering the update.",
    "Suma kontrolna z GitHuba różni się od podpisanej przez autora - nie instaluję.":
        "GitHub's checksum differs from the one signed by the author – not installing.",
    "Pobrany instalator nie zgadza się z podpisem autora (zła suma kontrolna) - spróbuj ponownie.":
        "The downloaded installer doesn't match the author's signature (bad checksum) – try again.",
    # język
    "Język": "Language",
    "Nutka uruchomi się ponownie po angielsku.": "Nutka will restart in Polish.",
    "Trwa pobieranie - przerwać je i zmienić język teraz?": "A download is in progress – stop it and switch language now?",
    # spotify_lista
    "To nie jest link do utworu, albumu ani playlisty Spotify.": "This is not a link to a Spotify track, album or playlist.",
    "Nieznany": "Unknown",
}
