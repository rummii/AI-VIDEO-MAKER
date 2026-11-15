"""Analyze every track in music/: duration, BPM, beat grid, drop point.
Writes music/library.json used by the video build pipeline.
"""
import json, os, glob

import numpy as np
import librosa

SR = 22050
out = {}
lib_path = os.path.join(MUSIC_DIR, "library.json") if (MUSIC_DIR := os.path.join(ROOT if False else ".", "music")) else None
try:
    out = json.load(open("music/library.json"))
except (FileNotFoundError, json.JSONDecodeError):
    out = {}

for path in sorted(glob.glob("music/*.mp3")):
    name = os.path.basename(path)
    if name in out and out[name].get("beats"):
        continue
    try:
        y, sr = librosa.load(path, sr=SR, mono=True)
        dur = len(y) / sr
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
        # energy envelope -> drop = biggest sustained jump in RMS
        rms = librosa.feature.rms(y=y, hop_length=512)[0]
        rms_t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
        # smooth + find frame where energy jumps most after 15s (skip intro)
        k = np.ones(43) / 43
        sm = np.convolve(rms, k, mode="same")
        start_f = int(15 * sr / 512)
        if len(sm) > start_f + 10:
            idx = start_f + int(np.argmax(np.diff(sm[start_f:])))
            drop_t = float(rms_t[idx])
            max_e_t = float(rms_t[int(np.argmax(sm))])
        else:
            drop_t, max_e_t = 0.0, 0.0
        out[name] = {
            "file": path,
            "duration": round(dur, 2),
            "bpm": round(float(np.atleast_1d(tempo)[0]), 1),
            "first_beat": round(float(beats[0]), 2) if len(beats) else 0,
            "drop_estimate": round(drop_t, 2),
            "max_energy_at": round(max_e_t, 2),
            "beats": [round(float(b), 3) for b in beats],
        }
        print(f"{name}: {dur:.1f}s, {out[name]['bpm']} BPM, drop~{drop_t:.1f}s, {len(beats)} beats")
    except Exception as e:
        print(f"{name}: FAILED - {e}")

with open("music/library.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("\nWrote music/library.json")
