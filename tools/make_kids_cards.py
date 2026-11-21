"""Generate bright, playful full-screen cards for a kids field-trip video."""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "kids_cards")
os.makedirs(OUT, exist_ok=True)
W, H = 1920, 1080
FONT = os.path.join(ROOT, "branding", "ArchivoBlack-400.ttf")
COLORS = [(255, 99, 132), (54, 162, 235), (255, 206, 59), (75, 207, 145), (155, 110, 245)]

CARDS = [
    ("kids_title.png", "FIELD TRIP!", "A day to remember", 0),
    ("kids_wow.png", "WOW!", "Look at that!", 1),
    ("kids_fun.png", "SO MUCH FUN!", None, 2),
    ("kids_end.png", "WHAT A DAY!", None, 3),
]

for name, title, sub, idx in CARDS:
    c = COLORS[idx % len(COLORS)]
    img = Image.new("RGB", (W, H), c)
    d = ImageDraw.Draw(img)
    # soft confetti dots
    import random
    random.seed(idx + 7)
    for _ in range(45):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.randint(8, 26)
        col = COLORS[(idx + random.randint(1, 3)) % len(COLORS)]
        d.ellipse([x-r, y-r, x+r, y+r], fill=col)
    f = ImageFont.truetype(FONT, 170)
    bb = d.textbbox((0, 0), title, font=f)
    d.text(((W - (bb[2]-bb[0])) // 2, H // 2 - 130), title, font=f, fill="white",
           stroke_width=8, stroke_fill=(0, 0, 0))
    if sub:
        f2 = ImageFont.truetype(FONT, 64)
        bb2 = d.textbbox((0, 0), sub, font=f2)
        d.text(((W - (bb2[2]-bb2[0])) // 2, H // 2 + 90), sub, font=f2, fill="white")
    path = os.path.join(OUT, name)
    img.save(path)
    print("saved", path)
