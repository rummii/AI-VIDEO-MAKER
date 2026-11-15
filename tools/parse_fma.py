import re, html as h, json, sys

src = sys.argv[1]
s = open(src, encoding="utf-8", errors="ignore").read()
blocks = re.findall(r"data-track-info='([^']+)'", s)
seen = set()
for b in blocks:
    d = json.loads(h.unescape(b))
    if d["handle"] in seen:
        continue
    seen.add(d["handle"])
    print(f"{d['handle']} | {d['title']} | {d['artistName']} | {d['downloadUrl']}")
