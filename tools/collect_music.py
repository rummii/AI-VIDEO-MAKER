import json, re, html as h, os, sys, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUT = "music"
os.makedirs(OUT, exist_ok=True)

# candidate handles -> which saved search file they came from
files = {
    "p2": r"C:\Users\ahmad\.local\share\opencode\tool-output\fma_p2.html",
    "bassdrop": r"C:\Users\ahmad\.local\share\opencode\tool-output\fma_bassdrop.html",
    "riddim": r"C:\Users\ahmad\.local\share\opencode\tool-output\fma_riddim.html",
}
candidates = [
    "dubstep-trap", "space-dubstep", "dubstep-damage", "dubstep-life",
    "modern-dubstep", "16_Expert_In_Mental_-_Pavillon_Dubstep", "riddim",
    "piano-dubstep-score", "epic-dubstep", "the-dubstep",
]

info = {}
for f in files.values():
    s = open(f, encoding="utf-8", errors="ignore").read()
    for b in re.findall(r"data-track-info='([^']+)'", s):
        d = json.loads(h.unescape(b))
        if d["handle"] in candidates:
            info[d["handle"]] = d

def license_of(page):
    cc = sorted(set(re.findall(r"creativecommons\.org/(?:licenses/|publicdomain/)[a-z0-9\-/]*", page, re.I)))
    return cc

def short(cc):
    if not cc:
        return "unknown"
    c = cc[0]
    if "publicdomain" in c:
        return "CC0"
    m = re.search(r"licenses/([a-z0-9\-]+)/", c)
    return "CC " + m.group(1).upper() if m else c

ok_licenses = ("CC0", "CC BY/", "CC BY-4", "CC BY-SA")

for handle in candidates:
    d = info.get(handle)
    if not d:
        print(f"{handle} | not found in search pages")
        continue
    url = d["url"]
    try:
        page = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore")
        lic = short(license_of(page))
    except Exception as e:
        print(f"{handle} | ERROR {e}")
        continue
    commercial = lic == "CC0" or lic in ("CC BY/4", "CC BY-SA")
    print(f"{handle} | {lic} | commercial_ok={commercial} | {d['artistName']} - {d['title']}")
    if not commercial:
        continue
    stream = f"https://freemusicarchive.org/track/{handle}/stream/"
    fname = os.path.join(OUT, f"{d['artistName']} - {d['title']}.mp3".replace("/", "-"))
    if os.path.exists(fname):
        print("   already have")
        continue
    try:
        urllib.request.urlretrieve(stream, fname)
        print(f"   downloaded -> {fname} ({os.path.getsize(fname)//1024} KB)")
    except Exception as e:
        print(f"   download failed: {e}")
