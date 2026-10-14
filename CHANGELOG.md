# Historia zmian

Format: najnowsze na górze. Sekcja wersji jest jednocześnie opisem „Co nowego”, który program pokazuje
przy proponowaniu aktualizacji – pisz ją dla zwykłego użytkownika.

## [1.5.0] – 2026-10-14

- **Nutka pobiera też filmy.** Obok pola „Link” jest przełącznik **Muzyka / Wideo**. W trybie „Wideo” link
  z YouTube (pojedynczy film albo cała playlista, także wielogodzinne nagrania) zapisuje się jako plik mp4,
  a obok wybierasz jakość: 1080p, 720p, 480p albo Najwyższa. Do 1080p Nutka bierze obraz H.264 i dźwięk AAC,
  więc plik gra na komputerze, telefonie i telewizorze bez dodatkowych kodeków.
- Filmy mają własny folder (domyślnie **Filmy \ Pobrane**), żeby nie mieszały się z muzyką. Pole „Zapisz do”
  pokazuje folder tego, co właśnie pobierasz.
- Nutka pamięta wybrane foldery, tryb i jakość między uruchomieniami.
- Ze Spotify, tak jak dotąd, pobiera się tylko muzyka – po wczytaniu listy program sam przełącza się na „Muzyka”.

In English: Nutka now downloads videos too. Next to the “Link” field there is a **Music / Video** switch: in “Video”
mode a YouTube link (a single video or a whole playlist, hours-long recordings included) is saved as an mp4 in the
quality you pick (1080p, 720p, 480p or Highest). Videos get their own folder (Videos \ Nutka by default), and Nutka
remembers your folders, mode and quality. Spotify stays music-only.

## [1.4.0] – 2026-10-09

- **Nutka mówi też po angielsku.** Na komputerze z Windowsem w innym języku niż polski program sam startuje
  po angielsku; język przełączysz przyciskiem „EN” / „PL” w prawym górnym rogu. Instrukcja jest w obu językach,
  a instalator pyta po angielsku, gdy Windows nie jest polski.
- Ekran startowy jest jeden dla obu języków, więc nie ma na nim polskich zdań.

In English: Nutka now speaks English. On a non-Polish Windows it starts in English; switch anytime with the
“EN” / “PL” button in the top-right corner. The guide and the installer are available in English as well.

## [1.3.0] – 2026-10-06

- **Spokojniejszy ekran**: pusty ekran i „Nic nie znaleziono” bez zbędnych nagłówków kolumn, pasek postępu
  pokazuje się tylko w trakcie pobierania (z procentem albo licznikiem „3/12” przy playliście), a „Następny”
  pojawia się dopiero podczas odsłuchu.
- Na dużym monitorze treść nie rozciąga się już na całą szerokość – okno wygląda dobrze zarówno
  zmaksymalizowane, jak i małe. Najmniejsze okno jest odrobinę większe, żeby wszystko się mieściło.
- Przyciski „Instrukcja” i „Postaw kawę autorowi” mają teraz ten sam, stonowany wygląd.
- „Sprawdź aktualizacje” w lewym dolnym rogu wygląda jak link – wcześniej trzeba było wiedzieć, że klika się
  w numer wersji.
- Drobiazgi: krótsza podpowiedź w wyszukiwarce, nazwa długiej playlisty skraca się do „…” zamiast zasłaniać
  przyciski, postęp utworu bez części dziesiętnej (64 % zamiast 64.0%), okno „Co nowego” bez pustego miejsca.
- **Instrukcja jako strona**: przycisk „Instrukcja” otwiera poradnik w przeglądarce – nadal działa bez internetu
  i jest ten sam, co na stronie programu.
- **Bezpieczniej**: każde wydanie jest podpisane cyfrowo kluczem autora – Nutka zainstaluje tylko wydanie
  z prawidłowym podpisem, pobrane z oficjalnego miejsca. Wklejony tekst traktuje jak link tylko wtedy, gdy
  naprawdę prowadzi do YouTube lub Spotify.

## [1.2.0] – 2026-10-05

- **Instrukcja w programie**: przycisk „Instrukcja” w prawym górnym rogu otwiera poradnik, jak korzystać
  z Nutki. Działa też bez internetu.
- Ładniejsza tabela wyników: za długie tytuły kończą się „…” zamiast uciętej litery, a utwory, których
  nie udało się pobrać, są wyróżnione na czerwono – od razu widać, co ponowić.
- Na liście mieści się więcej utworów, a pusty ekran podpowiada, od czego zacząć.
- Przycisk „Postaw kawę autorowi” dostał filiżankę i gładkie, zaokrąglone brzegi.

## [1.1.0] – 2026-10-02

- **Nowa nazwa: Nutka** (wcześniej Maestro), nowy nagłówek i ekran startowy. Przy pierwszej instalacji Nutka
  stoi obok starego programu – starego Maestro możesz odinstalować w Ustawieniach Windows.
- Podpowiedź w polu wyszukiwania mówi teraz wprost, co można wpisać albo wkleić (tytuł, wykonawca, link
  do utworu, albumu lub playlisty z YouTube i Spotify).
- W prawym górnym rogu jest przycisk „Postaw kawę autorowi” z podpisem MATCODE – całkowicie dobrowolny.
- **Playlisty i albumy ze Spotify**: wklej link, a Nutka pokaże listę utworów. Odznacz, czego nie chcesz,
  i kliknij „Pobierz zaznaczone”. Wczytanie playlisty trwa kilka sekund, pobieranie idzie po 3 utwory naraz.
- **Synchronizacja**: przy ponownym wczytaniu tej samej playlisty Nutka pokazuje, które utwory już masz,
  i pobiera tylko nowe.
- **Postęp i podsumowanie**: przy każdym utworze widać jego stan, a na końcu, ile się udało. Nieudane
  zostają zaznaczone – jedno kliknięcie i program próbuje jeszcze raz.
- Pliki ze Spotify mają dokładne tagi (tytuł, wykonawcy, album, numer, rok) i okładkę albumu.
- **Automatyczne aktualizacje programu**: gdy pojawi się nowa wersja, Nutka zaproponuje aktualizację
  i zainstaluje ją jednym kliknięciem. Ręcznie: kliknij numer wersji w lewym dolnym rogu.
- Odsłuch działa też dla utworów z listy Spotify.

## [1.0.0] – 2026-09-30

- Pierwsza wersja: wyszukiwarka YouTube Music, odsłuch (także całych albumów), pobieranie mp3 z YouTube
  i Spotify, ciemny motyw, ciche aktualizacje silnika pobierania.
