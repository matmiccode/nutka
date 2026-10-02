# Składniki innych autorów

Kod źródłowy Nutki jest na licencji MIT (plik `LICENSE`). Instalator `Nutka-Setup.exe` zawiera dodatkowo
programy i biblioteki innych autorów – każdy na własnej licencji. Ich kod źródłowy jest publicznie dostępny
pod poniższymi adresami. Część z nich jest na licencji GPL, dlatego cały kod Nutki jest jawny.

| Składnik | Do czego | Licencja | Kod źródłowy |
| --- | --- | --- | --- |
| Python | środowisko uruchomieniowe | PSF License | https://github.com/python/cpython |
| yt-dlp | pobieranie z YouTube | Unlicense | https://github.com/yt-dlp/yt-dlp |
| yt-dlp-ejs | obsługa zabezpieczeń YouTube | Unlicense | https://github.com/yt-dlp/ejs |
| Deno | uruchamianie skryptów YouTube | MIT | https://github.com/denoland/deno |
| FFmpeg (ffmpeg, ffprobe, ffplay) | konwersja do mp3, odsłuch | GPL-3.0 (build BtbN) | https://github.com/BtbN/FFmpeg-Builds, https://ffmpeg.org |
| ytmusicapi | wyszukiwarka YouTube Music | MIT | https://github.com/sigma67/ytmusicapi |
| spotapi | odczyt playlist i albumów Spotify | GPL-3.0 | https://pypi.org/project/spotapi/ (kod w paczce źródłowej) |
| mutagen | tagi i okładki w plikach mp3 | GPL-2.0-or-later | https://github.com/quodlibet/mutagen |
| CustomTkinter | wygląd okna | CC0-1.0 | https://github.com/TomSchimansky/CustomTkinter |
| Pillow | grafika | MIT-CMU | https://github.com/python-pillow/Pillow |
| curl_cffi, requests, certifi, websockets, brotli, pycryptodomex | sieć i szyfrowanie (zależności yt-dlp/spotapi) | MIT / Apache-2.0 / MPL-2.0 / BSD | https://pypi.org |
| PyInstaller | spakowanie programu do exe | GPL-2.0 z wyjątkiem dla bootloadera | https://github.com/pyinstaller/pyinstaller |
| Inno Setup | instalator | Inno Setup License | https://jrsoftware.org/isinfo.php |

Pełne teksty licencji: w katalogach poszczególnych bibliotek w folderze programu (`_internal\*.dist-info`)
oraz `narzedzia\LICENSE-ffmpeg.txt`.

Nutka nie jest powiązana z YouTube, Google ani Spotify. Nazwy i znaki towarowe należą do ich właścicieli.
