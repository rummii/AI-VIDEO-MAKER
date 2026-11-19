"""
brand_overlays.py - generates branded PNG overlays (watermark, intro card,
kinetic word pops, outro card) and returns the ffmpeg overlay plan.

All design constants come from branding/brand.json (site colors, fonts,
taglines) so every render is consistently on-brand.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load_brand():
    with open(os.path.join(ROOT, "branding", "brand.json"), encoding="utf-8") as f:
        return json.load(f)

def _font(path, size):
    return ImageFont.truetype(os.path.join(ROOT, path), size)

def _scaled(v, base, W):
    """scale a px value designed for 1080-wide base"""
    return int(v * W / 1080)

# ------------------------------------------------------------------ pieces
def _word_png(text, W, H, brand, accent=True, sub=None):
    """Kinetic word pop: big Archivo Black word, lime /// accent, optional sub line."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    disp = _font(brand["fonts"]["display"], _scaled(88, 88, W))
    col = brand["colors"]["white"]
    # measure
    tmp = d.textbbox((0, 0), text, font=disp)
    tw = tmp[2] - tmp[0]
    # auto-fit: shrink font if the text is wider than the frame allows
    size = _scaled(88, 88, W)
    while tw > W * 0.92 and size > 20:
        size = int(size * 0.92)
        disp = _font(brand["fonts"]["display"], size)
        tmp = d.textbbox((0, 0), text, font=disp)
        tw = tmp[2] - tmp[0]
    y = _scaled(300, 300, H)  # upper third, clear of reels UI
    x = (W - tw) // 2
    d.text((x, y), text, font=disp, fill=col)
    if accent:
        # lime slashes above the word, left-aligned to it
        acc = _font(brand["fonts"]["display"], _scaled(54, 54, W))
        ab = d.textbbox((0, 0), "///", font=acc)
        ay = y - int((ab[3] - ab[1]) * 1.35)
        d.text((x, ay), "///", font=acc, fill=brand["colors"]["logo_lime"])
    if sub:
        body = _font(brand["fonts"]["body"], _scaled(34, 34, W))
        sb = d.textbbox((0, 0), sub, font=body)
        d.text(((W - (sb[2] - sb[0])) // 2, y + tmp[3] - tmp[1] + _scaled(24, 24, W)),
               sub, font=body, fill=col)
    return img

def _image_png(W, H, path):
    """Fit an external image (sponsor/ad card) to a 9:16 frame.

    The ad is shown in full (centered, no cropping so its text stays readable)
    over a blurred, darkened copy of itself that fills the rest of the frame.
    """
    img = Image.open(path).convert("RGBA")
    # blurred cover background
    bg = img.copy()
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * scale) + 1, int(bg.height * scale) + 1), Image.LANCZOS)
    x0, y0 = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((x0, y0, x0 + W, y0 + H))
    bg = bg.filter(ImageFilter.GaussianBlur(50))
    bg = ImageEnhance.Brightness(bg).enhance(0.35)
    # foreground: full ad, scaled to frame width
    fg = img.copy()
    fw = int(W * 0.94)
    fg = fg.resize((fw, int(fg.height * fw / fg.width)), Image.LANCZOS)
    if fg.height > H:
        fh = int(H * 0.94)
        fg = fg.resize((int(fg.width * fh / fg.height), fh), Image.LANCZOS)
    bg.alpha_composite(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    return bg


def _intro_png(W, H, brand):
    """Intro: centered logo + ///UNLEASH YOUR SPIRIT."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    logo = Image.open(os.path.join(ROOT, brand["logos"]["rectangle"])).convert("RGBA")
    lw = int(W * 0.72)
    if W > H:  # 16:9 landscape: card logos 60% smaller
        lw = int(lw * brand["watermark"].get("landscape_card_shrink", 0.4))
    lh = int(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    ly = int(H * 0.34) - lh // 2
    img.alpha_composite(logo, ((W - lw) // 2, ly))
    disp = _font(brand["fonts"]["display"], _scaled(58, 58, W))
    t = brand["taglines"]["intro"]
    bb = d.textbbox((0, 0), t, font=disp)
    tw = bb[2] - bb[0]
    size = _scaled(58, 58, W)
    while tw > W * 0.92 and size > 20:
        size = int(size * 0.92)
        disp = _font(brand["fonts"]["display"], size)
        bb = d.textbbox((0, 0), t, font=disp)
        tw = bb[2] - bb[0]
    ty = ly + lh + _scaled(70, 70, H)
    d.text(((W - tw) // 2, ty), t, font=disp, fill=brand["colors"]["white"])
    # lime underline bar
    d.rectangle([(W - tw) // 2, ty + (bb[3] - bb[1]) + _scaled(18, 18, H),
                 (W - tw) // 2 + tw, ty + (bb[3] - bb[1]) + _scaled(30, 30, H)],
                fill=brand["colors"]["logo_lime"])
    return img

def _intro_dark_png(W, H, brand):
    """Siruma-style intro: grayscale logo centered on pure black.
    The faint 'GEAR' text is lifted to the logo's light accent tone so it
    stays legible on the dark card (same tone as the fish/scale artwork)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    logo = Image.open(os.path.join(ROOT, brand["logos"]["rectangle"])).convert("RGBA")
    r, g, b, a = logo.split()
    L = logo.convert("L")
    # GEAR (bottom-right small text) is near-black (~lum 30) -> lift it to
    # pure white so it stays legible on the dark card. The lime dot
    # (~lum 194 in grayscale) stays untouched via the <160 range.
    import numpy as np
    arr = np.array(L).astype(int)
    aa = np.array(a)
    h, w = arr.shape
    zone = np.zeros((h, w), bool)
    zone[int(h * 0.86):, int(w * 0.70):] = True   # GEAR text only
    sel = zone & (aa > 0) & (arr < 160)
    arr[sel] = 255
    L = Image.fromarray(arr.astype("uint8"))
    logo = Image.merge("RGBA", (L, L, L, a))
    lw = int(W * (0.55 if H > W else 0.42))
    lh = int(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, (H - lh) // 2))
    return img

def _outro_url_png(W, H, brand):
    """Siruma-style outro: minimal 'WWW.MONITORAGEAR.ME' over a soft scrim."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    band_top, band_bot = int(H * 0.40), int(H * 0.60)
    for yy in range(band_top, band_bot):
        a = int(100 * (1 - abs((yy - (band_top + band_bot) / 2) / ((band_bot - band_top) / 2))))
        d.line([(0, yy), (W, yy)], fill=(5, 5, 5, a))
    body = _font(brand["fonts"]["body_heavy"], _scaled(46, 46, W))
    t = "WWW." + brand["cta"]["outro_sub"].upper()
    bb = d.textbbox((0, 0), t, font=body)
    size = _scaled(46, 46, W)
    while bb[2] - bb[0] > W * 0.86 and size > 20:
        size = int(size * 0.92)
        body = _font(brand["fonts"]["body_heavy"], size)
        bb = d.textbbox((0, 0), t, font=body)
    ty = H // 2 - (bb[3] - bb[1]) // 2
    d.text(((W - (bb[2] - bb[0])) // 2, ty), t, font=body, fill=brand["colors"]["white"])
    return img

def _outro_png(W, H, brand):
    """Outro: dark scrim + logo + UNLEASH YOUR INNER MAVERICK + FOLLOW @monitorgear."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # soft dark scrim band across the middle for readability
    for i in range(H):
        pass
    band_top, band_bot = int(H * 0.28), int(H * 0.78)
    for yy in range(band_top, band_bot):
        a = int(150 * (1 - abs((yy - (band_top + band_bot) / 2) / ((band_bot - band_top) / 2))))
        d.line([(0, yy), (W, yy)], fill=(5, 5, 5, a))
    logo = Image.open(os.path.join(ROOT, brand["logos"]["rectangle"])).convert("RGBA")
    lw = int(W * 0.66)
    if W > H:  # 16:9 landscape: card logos 60% smaller
        lw = int(lw * brand["watermark"].get("landscape_card_shrink", 0.4))
    lh = int(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    ly = int(H * 0.42) - lh // 2
    img.alpha_composite(logo, ((W - lw) // 2, ly))
    disp = _font(brand["fonts"]["display"], _scaled(46, 46, W))
    t = brand["taglines"]["outro"]
    bb = d.textbbox((0, 0), t, font=disp)
    tw = bb[2] - bb[0]
    ty = ly + lh + _scaled(48, 48, H)
    d.text(((W - tw) // 2, ty), t, font=disp, fill=brand["colors"]["white"])
    body = _font(brand["fonts"]["body_heavy"], _scaled(40, 40, W))
    cta = brand["cta"]["outro_main"]
    cb = d.textbbox((0, 0), cta, font=body)
    cy = ty + (bb[3] - bb[1]) + _scaled(52, 52, H)
    cw = cb[2] - cb[0]
    # CTA pill in brand red
    pad = _scaled(26, 26, W)
    d.rounded_rectangle([(W - cw) // 2 - pad, cy - pad // 2, (W - cw) // 2 + cw + pad, cy + (cb[3] - cb[1]) + pad // 2],
                        radius=_scaled(14, 14, W), fill=brand["colors"]["primary_red"])
    d.text(((W - cw) // 2, cy), cta, font=body, fill=brand["colors"]["white"])
    body_l = _font(brand["fonts"]["body_light"], _scaled(28, 28, W))
    site = brand["cta"]["outro_sub"]
    sb = d.textbbox((0, 0), site, font=body_l)
    d.text(((W - (sb[2] - sb[0])) // 2, cy + (cb[3] - cb[1]) + _scaled(46, 46, H)),
           site, font=body_l, fill=brand["colors"]["white"])
    return img

def _watermark_png(W, brand, H=None, sponsors=None):
    path = brand["watermark"].get("file") or brand["logos"]["sticker"]
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        full = os.path.join(ROOT, brand["logos"]["sticker"])
    logo = Image.open(full).convert("RGBA")
    # size_px is specified for a 1080p base; scale with the shorter side so the
    # watermark keeps the same visual size at higher resolutions (4K -> 2x)
    scale = (min(W, H) / 1080) if H else 1.0
    side = int(brand["watermark"].get("size_px", 150) * scale)
    logo.thumbnail((side, side), Image.LANCZOS)   # fits exactly within 150x150
    if brand["watermark"].get("opacity", 1) < 1:
        a = logo.getchannel("A").point(lambda v: int(v * brand["watermark"]["opacity"]))
        logo.putalpha(a)
    if not sponsors:
        return logo
    # stack sponsor logos (fixed 150px each) below the watermark, right-aligned
    sp_side = int(brand["watermark"].get("sponsor_size_px", 150) * scale)
    gap = int(brand["watermark"].get("sponsor_gap_px", 26) * scale)
    op = brand["watermark"].get("opacity", 1)
    imgs = [logo]
    for sp in sponsors:
        try:
            img = Image.open(sp).convert("RGBA")
            img.thumbnail((sp_side, sp_side), Image.LANCZOS)
            if op < 1:
                a = img.getchannel("A").point(lambda v: int(v * op))
                img.putalpha(a)
            imgs.append(img)
        except Exception as e:
            print(f"  sponsor skipped {sp}: {e}")
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    col = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for i in imgs:
        col.alpha_composite(i, (w - i.width, y))
        y += i.height + gap
    return col

# ------------------------------------------------------------------ plan
def build_overlay_plan(project, shots, total, W, H, spec=None, sponsors=None):
    """Returns list of {png, start, end, mode} where mode is 'full' or 'watermark'.
    spec (optional, from shots JSON 'overlays' key) overrides defaults:
      [{"kind": "word|intro|outro", "text": "...", "sub": "...", "start": s, "end": e}]
    """
    brand = _load_brand()
    odir = os.path.join(ROOT, "tools", "overlays", project)
    os.makedirs(odir, exist_ok=True)
    plan = []

    wm = _watermark_png(W, brand, H, sponsors=sponsors)
    wm_path = os.path.join(odir, f"watermark_{W}x{H}.png")
    wm.save(wm_path)
    plan.append({"png": wm_path, "start": 0, "end": total, "mode": "watermark"})

    if spec is None:
        import random
        # word pool: brand words + the shorter alt taglines
        pool = list(brand["taglines"]["words"]) + list(brand["taglines"].get("alt", []))
        random.shuffle(pool)
        # boundaries of every interior shot (display-time), then pick at random
        cursor = 0.0
        boundaries = []
        for s in shots:
            boundaries.append(cursor)
            cursor += (s["end"] - s["start"]) / s.get("speed", 1.0)
        interior = boundaries[1:-1]
        random.shuffle(interior)
        n_pops = max(1, min(4, int(total // 12), len(interior)))
        spec = []
        t = shots[0]["end"] - shots[0]["start"]
        spec.append({"kind": "intro", "start": 0, "end": min(3.0, t)})
        POP = 3.0   # every B-roll message stays on screen 3 seconds
        placed = []
        for b in interior:
            s = b + 0.15
            e = s + POP
            if e > total - 3.0 - 0.2:      # keep clear of the outro card
                continue
            if any(s < pe and e > ps for ps, pe in placed):  # no overlaps
                continue
            spec.append({"kind": "word", "text": pool[len(placed) % len(pool)],
                         "start": s, "end": e})
            placed.append((s, e))
            if len(placed) >= n_pops:
                break
        spec.append({"kind": "outro", "start": max(total - 3.0, 0), "end": total})

    for k, o in enumerate(spec):
        kind = o.get("kind", "word")
        s, e = float(o["start"]), float(o["end"])
        if kind == "intro":
            png = _intro_png(W, H, brand)
        elif kind == "intro_dark":
            png = _intro_dark_png(W, H, brand)
        elif kind == "outro_url":
            png = _outro_url_png(W, H, brand)
        elif kind == "outro":
            png = _outro_png(W, H, brand)
        elif kind == "ad":
            f = o.get("file")
            if not os.path.isabs(f):
                f = os.path.join(ROOT, f)
            png = _image_png(W, H, f)
        else:
            png = _word_png(o.get("text", "ADRENALINE"), W, H, brand, sub=o.get("sub"))
        path = os.path.join(odir, f"ov_{k}_{kind}_{W}x{H}.png")
        png.save(path)
        plan.append({"png": path, "start": s, "end": e, "mode": "full"})
    return plan
