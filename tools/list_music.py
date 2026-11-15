import json
lib = json.load(open("music/library.json"))
for name, t in sorted(lib.items(), key=lambda kv: kv[1]["bpm"]):
    print(f"{t['bpm']:6.1f} BPM  drop~{t['drop_estimate']:6.1f}s  {name}")
