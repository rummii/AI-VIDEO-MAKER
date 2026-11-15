import os, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
os.makedirs("music", exist_ok=True)

tracks = [
    ("DUBSTEP ATTACK 1", "Soundtrack 4 Life", "dubstep-attack-1", "CC0"),
    ("DUBSTEP ATTACK 2", "Soundtrack 4 Life", "dubstep-attack-2", "CC0"),
    ("DUBSTEP ATTACK 3", "Soundtrack 4 Life", "dubstep-attack-3", "CC0"),
    ("DUBSTEP ATTACK 4", "Soundtrack 4 Life", "dubstep-attack-4", "CC0"),
    ("DUBSTEP ATTACK 5", "Soundtrack 4 Life", "dubstep-attack-5", "CC0"),
    ("DUBSTEP ATTACK 6", "Soundtrack 4 Life", "dubstep-attack-6", "CC0"),
    ("DUBSTEP ATTACK 8", "Soundtrack 4 Life", "dubstep-attack-8", "CC0"),
    ("DUBSTEP ATTACK 9", "Soundtrack 4 Life", "dubstep-attack-9", "CC0"),
    ("DUBSTEP ATTACK 666", "Soundtrack 4 Life", "dubstep-attack-666", "CC0"),
    ("Piano Dubstep Score", "Joseph Sacco", "piano-dubstep-score", "CC BY 4.0"),
]

for title, artist, handle, lic in tracks:
    fname = os.path.join("music", f"{artist} - {title}.mp3")
    if os.path.exists(fname):
        print(f"skip (exists): {fname}")
        continue
    url = f"https://freemusicarchive.org/track/{handle}/stream/"
    try:
        urllib.request.urlretrieve(urllib.request.Request(url, headers=UA).full_url, fname)
        print(f"OK  {fname}  {os.path.getsize(fname)//1024} KB  [{lic}]")
    except Exception as e:
        print(f"FAIL {handle}: {e}")
