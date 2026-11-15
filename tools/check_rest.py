import re, urllib.request

ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
for n in ["3", "5", "6", "9"]:
    url = f"https://freemusicarchive.org/music/soundtrack-4-life/dubstep-attack/dubstep-attack-{n}/"
    req = urllib.request.Request(url, headers=ua)
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    cc = sorted(set(re.findall(r"creativecommons\.org/(?:licenses/|publicdomain/)[a-z0-9\-/]*", page, re.I)))
    print(f"dubstep-attack-{n} | {cc}")
