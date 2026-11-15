"""Study the user's original edit (clips/Siruma.mp4) to reverse-engineer
their editing philosophy: how cuts relate to the music (beats, drops, energy).

Method:
1. Hard cut timestamps come from ffmpeg scene detection (deduped by hand below).
2. Load the baked-in audio with librosa: beat grid, onset strength, RMS energy.
3. For each cut: distance to nearest beat, local energy percentile.
4. Report: BPM, cut cadence, beat-alignment stats, energy at cuts.
"""
import numpy as np, librosa

CUTS = [2.17, 2.77, 13.67, 24.70, 25.43, 25.77, 43.93, 54.43, 66.17, 66.67, 104.83]

y, sr = librosa.load(r"C:\Users\ahmad\AppData\Local\Temp\opencode\siruma_audio.wav", sr=22050, mono=True)
dur = len(y) / sr
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
tempo = float(np.atleast_1d(tempo)[0])
onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
rms = librosa.feature.rms(y=y, hop_length=512)[0]
rms_t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
on_t = librosa.frames_to_time(np.arange(len(onset)), sr=sr, hop_length=512)

print(f"duration {dur:.1f}s | BPM {tempo:.1f} | beats {len(beats)}")
print(f"beat interval {60/tempo:.3f}s")

def nearest(arr, t):
    i = int(np.argmin(np.abs(arr - t)))
    return float(arr[i]), abs(float(arr[i]) - t)

def pct_env(arr, t, win=0.5):
    """energy percentile of local window vs whole track"""
    m = (arr >= t - win) & (arr <= t + win)
    if not m.any():
        return 0.0
    return float((arr[m] > np.median(arr)).mean())

print(f"\n{'cut':>7} | {'nearest beat':>12} | {'off(ms)':>7} | {'rms pct':>7} | {'onset pct':>9}")
offs = []
for c in CUTS:
    b, off = nearest(beats, c)
    offs.append(off)
    print(f"{c:7.2f} | {b:12.2f} | {off*1000:7.0f} | {pct_env(rms, c)*100:6.0f}% | {pct_env(onset, c)*100:8.0f}%")
offs = np.array(offs) * 1000
print(f"\nbeat-alignment: mean offset {offs.mean():.0f}ms, median {np.median(offs):.0f}ms, within 100ms: {(offs<=100).mean()*100:.0f}%")

# RMS profile summary: section energies
for label, a, b in [("intro 0-13", 0, 13.7), ("A 13.7-24.7", 13.7, 24.7), ("burst 24.7-26", 24.7, 26.2),
                    ("B 26-44", 26.2, 43.9), ("C 44-54", 43.9, 54.4), ("D 54-66", 54.4, 66.2),
                    ("E 66-105", 66.7, 104.8), ("out 105-108", 104.8, 108.5)]:
    m = (rms_t >= a) & (rms_t < b)
    if m.any():
        print(f"{label:16} rms mean {rms[m].mean():.4f} max {rms[m].max():.4f}")

# onset cadence: how often cuts happen
cs = np.array(CUTS)
iv = np.diff(cs)
print(f"\ncut intervals: {np.round(iv, 1)}")
print(f"mean gap {iv.mean():.1f}s, min {iv.min():.1f}s")
