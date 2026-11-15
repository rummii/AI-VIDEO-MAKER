import json, re, urllib.request

urls = {
    "dubstep": "https://freemusicarchive.org/music/nitzi/nitzi/dubstep/",
    "epic-dubstep-short-version-4": "https://freemusicarchive.org/music/blacktrendmusic/epic-dubstep/epic-dubstep-short-version-4/",
    "dubstep-attack-4": "https://freemusicarchive.org/music/soundtrack-4-life/dubstep-attack/dubstep-attack-4/",
    "dubstep-attack-666": "https://freemusicarchive.org/music/soundtrack-4-life/dubstep-attack/dubstep-attack-666/",
    "dubstep-attack-1": "https://freemusicarchive.org/music/soundtrack-4-life/dubstep-attack/dubstep-attack-1/",
    "dubstep-attack-2": "https://freemusicarchive.org/music/soundtrack-4-life/dubstep-attack/dubstep-attack-2/",
    "dubstep-attack-8": "https://freemusicarchive.org/music/soundtrack-4-life/dubstep-attack/dubstep-attack-8/",
    "epic-dubstep-short-version-1": "https://freemusicarchive.org/music/blacktrendmusic/epic-dubstep/epic-dubstep-short-version-1/",
    "epic-dubstep-short-version-2": "https://freemusicarchive.org/music/blacktrendmusic/epic-dubstep/epic-dubstep-short-version-2/",
    "orchestral-dubstepmp3": "https://freemusicarchive.org/music/yeah-music/orchestral-dubstep/orchestral-dubstepmp3/",
    "orchestral-dubstep-short-02mp3": "https://freemusicarchive.org/music/yeah-music/orchestral-dubstep/orchestral-dubstep-short-02mp3/",
    "orchestral-dubstep-short-08mp3": "https://freemusicarchive.org/music/yeah-music/orchestral-dubstep/orchestral-dubstep-short-08mp3/",
}

ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
for name, url in urls.items():
    try:
        req = urllib.request.Request(url, headers=ua)
        page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"{name} | ERROR {e}")
        continue
    cc = sorted(set(re.findall(r"creativecommons\.org/(?:licenses/|publicdomain/)[a-z0-9\-/]*", page, re.I)))
    lic_txt = ""
    m = re.search(r"license[\"'>\s:=]+([^<\"]{5,80}license[^<\"]{0,40})", page, re.I)
    if m:
        lic_txt = re.sub(r"\s+", " ", m.group(1)).strip()
    print(f"{name} | {cc} | {lic_txt}")
