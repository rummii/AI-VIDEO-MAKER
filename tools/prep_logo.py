"""Prepare branding/logo_round.png from the user-provided 'Artboard 1.png':
- ensure RGBA
- if the background is opaque white, knock out near-white to transparency
- preview: composite the 150x150 watermark on dark + bright backgrounds
"""
import os, shutil
from PIL import Image

src = "branding/Artboard 1.png"
dst = "branding/logo_round.png"
img = Image.open(src).convert("RGBA")
print("size:", img.size, "mode:", img.mode)

corner = img.getpixel((2, 2))
print("corner pixel:", corner)

px = img.load()
W, H = img.size
knocked = 0
if corner[3] > 250 and corner[0] > 245 and corner[1] > 245 and corner[2] > 245:
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a > 0 and r >= 245 and g >= 245 and b >= 245:
                px[x, y] = (r, g, b, 0)
                knocked += 1
    print(f"knocked out {knocked} white px ({100*knocked/(W*H):.1f}%)")
img.save(dst)
print("saved", dst)

# build the 150x150 watermark preview
wm = Image.open(dst).convert("RGBA")
wm.thumbnail((150, 150), Image.LANCZOS)
for name, bg in [("dark", (20, 20, 20)), ("bright", (190, 220, 170))]:
    canvas = Image.new("RGBA", (300, 160), bg + (255,))
    canvas.alpha_composite(wm, (10, 5))
    canvas.convert("RGB").save(f"C:/Users/ahmad/AppData/Local/Temp/opencode/wm_{name}.jpg", quality=90)
print("previews written")
