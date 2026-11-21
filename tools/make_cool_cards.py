"""Cooler cards for 9-12 year olds - field trip adventure."""
import os, random
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'kids_cards')
os.makedirs(OUT, exist_ok=True)
W, H = 1920, 1080
FONT = os.path.join(ROOT, 'branding', 'ArchivoBlack-400.ttf')
COLORS = [(24, 28, 38), (16, 96, 150), (212, 56, 48), (20, 130, 100), (110, 60, 180), (220, 130, 20)]
CARDS = [
    ('trip_title.png', 'FIELD TRIP 2026!', 'The adventure begins', 0),
    ('trip_zipline.png', 'ZIPLINE!', None, 1),
    ('trip_park.png', 'THEME PARK!', None, 2),
    ('trip_water.png', 'SPLASH ZONE!', None, 3),
    ('trip_gofaster.png', 'GO FASTER!', None, 4),
    ('trip_end.png', 'BEST DAY EVER!', None, 5),
]
for name, title, sub, idx in CARDS:
    c = COLORS[idx % len(COLORS)]
    img = Image.new('RGB', (W, H), c)
    d = ImageDraw.Draw(img)
    random.seed(idx + 11)
    for _ in range(36):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.randint(10, 30)
        col = COLORS[random.randint(0, len(COLORS)-1)]
        d.ellipse([x-r, y-r, x+r, y+r], outline=col, width=7)
    f = ImageFont.truetype(FONT, 150)
    bb = d.textbbox((0, 0), title, font=f)
    d.text(((W-(bb[2]-bb[0]))//2, H//2-110), title, font=f, fill='white')
    if sub:
        f2 = ImageFont.truetype(FONT, 58)
        bb2 = d.textbbox((0,0), sub, font=f2)
        d.text(((W-(bb2[2]-bb2[0]))//2, H//2+90), sub, font=f2, fill=(255,215,70))
    img.save(os.path.join(OUT, name))
    print('saved', name)
