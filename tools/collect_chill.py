"""Curate chill-house/deep-house/melodic-electronic tracks from FMA search pages.
Only CC0 or CC BY (commercial OK) tracks are downloaded into music/.
Writes music/genre_index.json so the build engine knows which tracks are chill.
"""
import json, os, re, html as h, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUT = "music"
os.makedirs(OUT, exist_ok=True)

BASE = r"C:\Users\ahmad\.local\share\opencode\tool-output"
files = {
    "chill_house": BASE + r"\fma_chill_house.html",
    "deep_house": BASE + r"\fma_deep_house.html",
    "melodic_electronic": BASE + r"\fma_melodic_electronic.html",
    "indie_dance": BASE + r"\fma_indie_dance.html",
    "atmospheric_electronic": BASE + r"\fma_atmospheric_electronic.html",
    "lounge": BASE + r"\fma_lounge.html",
}

def short_license(cc_list):
    if not cc_list:
        return "unknown"
    c = cc_list[0]
    if "publicdomain" in c:
        return "CC0"
    m = re.search(r"licenses/([a-z0-9\-]+)/", c)
    return "CC " + m.group(1).upper().rstrip("/") if m else c

def commercial_ok(lic):
    return lic == "CC0" or lic == "CC BY"

# collect unique tracks with their page url + genre buckets
tracks = {}
for bucket, f in files.items():
    try:
        s = open(f, encoding="utf-8", errors="ignore").read()
    except FileNotFoundError:
        continue
    for b in re.findall(r"data-track-info='([^']+)'", s):
        d = json.loads(h.unescape(b))
        handle = d["handle"]
        t = tracks.setdefault(handle, {
            "handle": handle, "title": d["title"], "artist": d["artistName"],
            "page_url": d["url"], "genres": [], "duration": d.get("duration"),
        })
        t["genres"].append(bucket)

print(f"{len(tracks)} unique candidate tracks")

chill = []
for handle, t in tracks.items():
    try:
        page = urllib.request.urlopen(urllib.request.Request(t["page_url"], headers=UA), timeout=30).read().decode("utf-8", "ignore")
        lic = short_license(sorted(set(re.findall(r"creativecommons\.org/(?:licenses/|publicdomain/)[a-z0-9\-/]*", page, re.I))))
    except Exception as e:
        print(f"  {handle}: license check failed ({e})")
        continue
    if not commercial_ok(lic):
        continue
    fname = os.path.join(OUT, f"{t['artist']} - {t['title']}.mp3".replace("/", "-"))
    if os.path.exists(fname):
        chill.append({**t, "license": lic, "file": fname})
        continue
    stream = f"https://freemusicarchive.org/track/{handle}/stream/"
    try:
        import subprocess
        subprocess.run(["curl.exe", "-sL", "-A", "Mozilla/5.0", "-o", fname, stream],
                       check=True, timeout=300)
        if os.path.getsize(fname) < 100_000:
            os.remove(fname)
            raise RuntimeError("file too small / blocked")
        print(f"  + {t['artist']} - {t['title']} [{lic}]")
        chill.append({**t, "license": lic, "file": fname})
    except Exception as e:
        print(f"  x {handle}: download failed ({e})")

# keep license note for credits
try:
    credits = open("MUSIC_CREDITS.md", encoding="utf-8").read()
except FileNotFoundError:
    credits = ""
new_rows = []
for t in chill:
    key = t["artist"]
    if key not in credits:
        new_rows.append(f"| {t['title']} | {t['artist']} | {t['license']} | {'Yes (CC BY)' if t['license'] != 'CC0' else 'No'} |")
if new_rows:
    with open("MUSIC_CREDITS.md", "a", encoding="utf-8") as f:
        f.write("\n## Chill House / Electronic collection (added)\n\n| Track | Artist | License | Attribution needed |\n|---|---|---|---|\n")
        f.write("\n".join(new_rows) + "\n")

with open("music/genre_index.json", "w", encoding="utf-8") as f:
    json.dump({"chill": [t["file"] for t in chill]}, f, indent=2)
print(f"\n{len(chill)} commercial-safe chill tracks collected")
