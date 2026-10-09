"""Grafiki Nutki rysowane w Pillow (MATCODE): nagłówek okna (po polsku i po angielsku) i ekran startowy.

  build/venv/Scripts/python.exe grafika.py   -> naglowek.png, naglowek-en.png, splash.png

Nagłówek: gradient róż -> fiolet, nutka, nazwa i podpis pod nią; 2x rozdzielczość (CTkImage skaluje pod DPI),
szerszy niż okno - nadmiar po prawej się przycina, dalej jednolity FIOLET z app.py. Ekran startowy jest jeden
na oba języki (PyInstaller wkłada go do exe przed startem Pythona), więc nie ma na nim żadnego zdania po polsku.
Czcionki: Segoe UI z Windows.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

TU = Path(__file__).parent
FONTY = Path(r"C:\Windows\Fonts")
POCZ, KON = (236, 72, 153), (142, 47, 184)  # róż -> fiolet (FIOLET w app.py = #8E2FB8)
BIALY = (255, 255, 255)
PODPISY = {"": "muzyka z YouTube i Spotify", "-en": "music from YouTube and Spotify"}


def nuta(d: ImageDraw.ImageDraw, x: float, y: float, s: float):
    """Nutka jak w ikonie: dwie główki, dwie laski i belka."""
    d.ellipse([x, y + 420 * s, x + 220 * s, y + 580 * s], fill=BIALY)
    d.ellipse([x + 330 * s, y + 360 * s, x + 550 * s, y + 520 * s], fill=BIALY)
    d.rectangle([x + 170 * s, y + 60 * s, x + 220 * s, y + 500 * s], fill=BIALY)
    d.rectangle([x + 500 * s, y, x + 550 * s, y + 440 * s], fill=BIALY)
    d.polygon([(x + 170 * s, y + 60 * s), (x + 550 * s, y), (x + 550 * s, y + 110 * s), (x + 170 * s, y + 170 * s)],
              fill=BIALY)


def naglowek(koncowka: str, podpis: str):
    S = 2
    W, H = 1600, 84          # logicznie
    KONIEC_GRADIENTU = 1100  # dalej jednolity kolor ramki nagłówka
    img = Image.new("RGB", (W * S, H * S), KON)
    d = ImageDraw.Draw(img)
    for x in range(KONIEC_GRADIENTU * S):
        t = x / (KONIEC_GRADIENTU * S)
        d.line([(x, 0), (x, H * S)], fill=tuple(int(a + (b - a) * t) for a, b in zip(POCZ, KON)))
    nuta(d, 24 * S, 17 * S, 0.087 * S)
    tytul = ImageFont.truetype(str(FONTY / "segoeuib.ttf"), 30 * S)
    opis = ImageFont.truetype(str(FONTY / "segoeui.ttf"), 13 * S)
    d.text((86 * S, 12 * S), "Nutka", font=tytul, fill=BIALY)
    d.text((88 * S, 52 * S), podpis, font=opis, fill=(255, 228, 242))
    img.save(TU / f"naglowek{koncowka}.png", optimize=True)


def splash():
    S = 2  # rysujemy w 2x i zmniejszamy - gładkie krawędzie
    W, H = 560, 320
    img = Image.new("RGB", (W * S, H * S))
    d = ImageDraw.Draw(img)
    for y in range(H * S):  # gradient jak w ikonie: róż -> fiolet
        t = y / (H * S)
        d.line([(0, y), (W * S, y)], fill=(int(236 - 70 * t), int(72 - 35 * t), int(153 + 45 * t)))
    glow = Image.new("L", (W * S, H * S), 0)  # delikatna poświata w prawym górnym rogu
    ImageDraw.Draw(glow).ellipse([W * S * 0.55, -H * S * 0.6, W * S * 1.4, H * S * 0.7], fill=40)
    img.paste(BIALY, (0, 0), glow.filter(ImageFilter.GaussianBlur(60 * S)))
    d = ImageDraw.Draw(img)
    nuta(d, 52 * S, 78 * S, 0.24 * S)
    tytul = ImageFont.truetype(str(FONTY / "segoeuib.ttf"), 64 * S)
    opis = ImageFont.truetype(str(FONTY / "segoeui.ttf"), 17 * S)
    maly = ImageFont.truetype(str(FONTY / "seguisb.ttf"), 13 * S)
    d.text((210 * S, 82 * S), "Nutka", font=tytul, fill=BIALY)
    d.text((214 * S, 168 * S), "YouTube · Spotify → mp3", font=opis, fill=(255, 235, 245))  # bez słów, które trzeba tłumaczyć
    d.rounded_rectangle([52 * S, 248 * S, (W - 52) * S, 254 * S], radius=3 * S, fill=(214, 120, 190))
    d.rounded_rectangle([52 * S, 248 * S, 250 * S, 254 * S], radius=3 * S, fill=BIALY)
    podpis = "MATCODE"
    d.text(((W - 52) * S - d.textlength(podpis, font=maly), 266 * S), podpis, font=maly, fill=(255, 235, 245))
    img.resize((W, H), Image.LANCZOS).save(TU / "splash.png", optimize=True)


if __name__ == "__main__":
    for koncowka, podpis in PODPISY.items():
        naglowek(koncowka, podpis)
    splash()
    print("gotowe:", sorted(p.name for p in TU.glob("naglowek*.png")) + ["splash.png"])
