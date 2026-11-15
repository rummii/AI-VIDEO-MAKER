"""Build branding/brand.json: colors sampled from the official logo + site CSS,
fonts, taglines, socials, CTA. One source of truth for every video render.
"""
import json, os
from PIL import Image

def hex2rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]

def rgb2hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

# --- sample dominant colors from the rectangle logo -------------------------
img = Image.open("branding/logo_rectangle.webp").convert("RGBA")
img.thumbnail((200, 200))
counts = {}
for r, g, b, a in img.getdata():
    if a < 128:            # transparent
        continue
    # quantize to reduce noise
    q = (r // 16 * 16, g // 16 * 16, b // 16 * 16)
    counts[q] = counts.get(q, 0) + 1
top = sorted(counts.items(), key=lambda kv: -kv[1])[:12]
print("top logo colors (quantized):")
for c, n in top:
    print(f"  {rgb2hex(c)}  x{n}")

# classify: gray (low saturation), lime (high g, low-ish r), other
import colorsys
gray, lime, other = None, None, None
for c, n in top:
    r, g, b = c
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s < 0.2 and gray is None and v > 0.2 and n > 50:
        gray = rgb2hex(c)
    elif h * 360 > 60 and h * 360 < 130 and s > 0.3 and lime is None:
        lime = rgb2hex(c)

brand = {
    "name": "Monitor Gear",
    "site": "https://www.monitorgear.me",
    "colors": {
        "primary_red": "#ff0000",       # site btn-primary / accent
        "logo_lime": lime or "#b6c424", # sampled from logo lizard
        "logo_gray": gray or "#7a7a7a", # sampled from logo wordmark
        "dark_maroon": "#320707",       # site dark support color
        "white": "#ffffff",
        "black": "#0a0a0a",
    },
    "fonts": {
        "display": "branding/ArchivoBlack-400.ttf",   # Archivo Black - headlines
        "body": "branding/Sora-600.ttf",              # Sora semibold - support text
        "body_light": "branding/Sora-400.ttf",
        "body_heavy": "branding/Sora-800.ttf",
    },
    "logos": {
        "rectangle": "branding/logo_rectangle.webp",
        "sticker": "branding/logo_sticker.png",
    },
    "taglines": {
        "intro": "///UNLEASH YOUR SPIRIT",
        "outro": "UNLEASH YOUR INNER MAVERICK",
        "alt": ["ELEVATE YOUR THRILLS", "WHERE FEAR MEETS FUN"],
        "words": ["ADRENALINE", "CHALLENGES", "ADVENTURE", "EXPLORATION"],
    },
    "social": {"instagram": "@monitorgear", "facebook": "monitorgearsports"},
    "cta": {"outro_main": "FOLLOW @monitorgear", "outro_sub": "monitorgear.me"},
    "watermark": {
        "corner": "top-right",       # safe from Reels/TikTok UI (UI is bottom+top-left)
        "width_frac": 0.28,          # logo width relative to video width
        "opacity": 0.85,
        "margin_frac": 0.03,
    },
}
with open("branding/brand.json", "w", encoding="utf-8") as f:
    json.dump(brand, f, indent=2)
print("\nWrote branding/brand.json")
print("lime:", lime, "| gray:", gray)
