"""
edit_style.py - "Siruma style": music-first editing learned from the user's
original edit (clips/Siruma.mp4, 108.5s @ 152 BPM).

Measured philosophy:
  - cuts land on musical energy shifts & phrase boundaries (~10-12s apart),
    snap-tight on section changes (one cut was 2ms off the beat)
  - rapid 0.3-0.7s texture-cutaway bursts exactly at musical hits
    (B-roll bridges between scenes)
  - long immersive holds on the money shot during the peak (theirs: 38s)
  - character transitions: glitch/static bridge after the intro,
    flash-to-black flicker into the biggest section
  - dark logo intro card, minimal URL outro card, fade to black
  - a quiet breakdown gets its own calm scene, entered on a beat

build_plan() produces a shots JSON (with bridge shot kinds "black"/"noise"/
"texture") that tools/make_video.py build renders. Energy sections are cached
into music/library.json as "energy10" (10 Hz normalized envelope).
"""
import json, os, subprocess

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = os.path.join(ROOT, "tools", "ffmpeg", "ffmpeg-9.0.2-essentials_build", "bin", "ffmpeg.exe")
LIB = os.path.join(ROOT, "music", "library.json")


# ------------------------------------------------------------ footage scout
def scout_clip(path):
    """Sample tiny frames, score motion + colorfulness per bucket."""
    w, h = 160, 90
    probe = subprocess.run(
        [FFMPEG.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error",
         "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1", path],
        capture_output=True, text=True, timeout=120)
    try:
        true_dur = float(probe.stdout.strip())
    except (ValueError, AttributeError):
        true_dur = 0.0
    # ~1 frame per 2s for long clips; up to 4fps for short ones
    fps = min(4.0, max(1.0, 3.0 / max(true_dur, 1.0) * 20)) if true_dur else 1.0
    cmd = [FFMPEG, "-i", path, "-skip_frame", "nokey", "-vf", f"fps={fps:.3f},scale=160:90",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.run(cmd, capture_output=True, timeout=900)
    n = len(p.stdout) // (w * h * 3)
    if n < 8:
        cmd = [FFMPEG, "-i", path, "-skip_frame", "nokey", "-vf", "fps=4,scale=160:90",
               "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
        p = subprocess.run(cmd, capture_output=True, timeout=900)
        n = len(p.stdout) // (w * h * 3)
        fps = 4.0
    if n < 8:
        raise RuntimeError(f"not enough frames sampled from {path}")
    arr = np.frombuffer(p.stdout[:n * w * h * 3], np.uint8).reshape(n, h, w, 3).astype(np.float32)
    luma = arr[..., 0] * 0.114 + arr[..., 1] * 0.587 + arr[..., 2] * 0.299
    motion = np.concatenate([[0], np.abs(np.diff(luma, axis=0)).mean(axis=(1, 2))])
    colorf = (arr.max(axis=3) - arr.min(axis=3)).mean(axis=(1, 2))
    step = 1.0 / fps
    dur = n * step
    dur = true_dur if true_dur > 0 else dur
    return {"path": path, "duration": dur, "t": np.arange(n) * step, "step": step,
            "motion": motion, "color": colorf}


def _smooth(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, mode="same")


def _z(x):
    s = x.std()
    return (x - x.mean()) / (s if s > 1e-6 else 1.0)


def pick_windows(sc):
    """Role windows from one scout: money/action/scenic/calm, each (start,end)."""
    dt = sc.get("step", 2.0)
    n = len(sc["t"])
    mo, co = _z(_smooth(sc["motion"], 2)), _z(_smooth(sc["color"], 2))
    edge = max(2, int(2 / dt))
    free = np.ones(n, bool)
    free[:edge] = free[-edge:] = False

    def win(i, length):
        return (max(sc["t"][i], 0.0), min(sc["t"][i] + length, sc["duration"]))

    # money: best-scoring ~12s window (colorfulness weighted — brilliant
    # scenery + action beats pure motion for the money shot)
    L = min(max(int(12 / dt), 3), n)
    score = 0.45 * mo + 0.55 * co
    c = np.convolve(score * free, np.ones(L) / L, mode="valid")
    mi = int(np.argmax(c))
    money = win(mi, L * dt)

    def excl(w):
        i0, i1 = int(w[0] / dt), int(w[1] / dt)
        m = free.copy()
        m[max(0, i0 - 2):min(n, i1 + 2)] = False
        return m

    # action: highest motion outside money
    ma = np.where(excl(money), mo, -1e9)
    ai = int(np.argmax(ma))
    action = win(max(0, ai - 1), 8.0)
    # second action zone, further away
    ma2 = ma.copy()
    i0, i1 = int(action[0] / dt), int(action[1] / dt)
    ma2[max(0, i0 - 2):min(n, i1 + 2)] = -1e9
    ai2 = int(np.argmax(ma2))
    action2 = win(max(0, ai2 - 1), 8.0)
    # calm: lowest motion
    mc = np.where(free, mo, 1e9)
    ci = int(np.argmin(mc))
    calm = win(max(0, ci - 1), 6.0)
    # scenic: colorful but quiet
    quiet = mo < np.median(mo[free])
    ms = np.where(free & quiet, co, -1e9)
    si = int(np.argmax(ms))
    scenic = win(max(0, si - 1), 6.0)
    si2 = si
    ms2 = ms.copy()
    i0, i1 = int(scenic[0] / dt), int(scenic[1] / dt)
    ms2[max(0, i0 - 2):min(n, i1 + 2)] = -1e9
    si2 = int(np.argmax(ms2))
    scenic2 = win(max(0, si2 - 1), 6.0)

    return {"money": money, "action": action, "action2": action2,
            "calm": calm, "scenic": scenic, "scenic2": scenic2,
            "scores": {"money": float(c[mi]), "action": float(mo[ai]),
                       "calm": float(-mo[ci]), "scenic": float(co[si])}}


# ------------------------------------------------------------ music energy
def energy_sections(track_name, track):
    """Calm/build/peak sections of the track; cached in library.json."""
    lib = json.load(open(LIB))
    t = lib[track_name]
    if "energy10" not in t:
        import librosa
        y, sr = librosa.load(os.path.join(ROOT, "music", track_name), sr=22050, mono=True)
        rms = librosa.feature.rms(y=y, hop_length=512)[0]
        # downsample to 10 Hz (block max keeps transients)
        step = int(sr * 0.1 / 512)
        m = len(rms) // step
        env = rms[:m * step].reshape(m, step).max(axis=1)
        env = env / max(env.max(), 1e-9)
        t["energy10"] = [round(float(v), 4) for v in env]
        json.dump(lib, open(LIB, "w"), indent=2)
    env = np.array(t["energy10"])
    dt = 0.1
    sm = _smooth(env, 30)  # 3s
    hi, lo = np.percentile(sm, 78), np.percentile(sm, 40)
    cls = np.where(sm > hi, "peak", np.where(sm < lo, "calm", "build"))
    runs, i = [], 0
    while i < len(cls):
        j = i
        while j < len(cls) and cls[j] == cls[i]:
            j += 1
        runs.append([float(i * dt), float(j * dt), str(cls[i])])
        i = j
    # merge tiny runs into previous
    out = []
    for r in runs:
        if out and r[1] - r[0] < 1.2:
            out[-1][1] = r[1]
        elif out and out[-1][2] == r[2]:
            out[-1][1] = r[1]
        else:
            out.append(r)
    return out


# ------------------------------------------------------------ planner
def _plan_structure(D):
    """Segment skeleton scaled to D: (kind, base_duration, role, min_dur)."""
    intro = max(1.8, min(2.4, D * 0.055))
    outro = max(2.8, min(4.0, D * 0.09))
    segs = [
        {"kind": "black", "dur": intro, "role": "intro", "min": 1.5},
        {"kind": "noise", "dur": 0.4, "role": "glitch", "min": 0.3},
        {"kind": "clip", "dur": D * 0.24, "role": "action", "min": 2.5},
        {"kind": "clip", "dur": D * 0.15, "role": "scenic", "min": 2.0},
        {"kind": "texture", "dur": 0.42, "role": "burst1", "min": 0.3},
        {"kind": "texture", "dur": 0.34, "role": "burst2", "min": 0.28},
        {"kind": "texture", "dur": 0.28, "role": "burst3", "min": 0.25},
        {"kind": "clip", "dur": D * 0.13, "role": "action2", "min": 2.0},
        {"kind": "clip", "dur": D * 0.10, "role": "calm", "min": 1.8},
        {"kind": "black", "dur": 0.14, "role": "flash", "min": 0.12},
        {"kind": "clip", "dur": D * 0.19, "role": "money", "min": 3.0},
        {"kind": "clip", "dur": outro, "role": "scenic2", "min": 2.2},
    ]
    # scale the flexible clips so the total is exactly D
    fixed = sum(s["dur"] for s in segs if s["kind"] in ("black", "noise", "texture"))
    flex = sum(s["dur"] for s in segs if s["kind"] == "clip")
    k = (D - fixed) / flex
    for s in segs:
        if s["kind"] == "clip":
            s["dur"] *= k
    return segs


def build_plan(clip_paths, track_name, track, D, seed=None):
    if seed is not None:
        np.random.seed(seed)
        import random
        random.seed(seed)
    beats = track["beats"]
    segs = _plan_structure(D)

    # scout all clips once
    scouts = []
    for p in clip_paths:
        try:
            sc = scout_clip(p)
            sc["wins"] = pick_windows(sc)
            scouts.append(sc)
        except Exception as e:
            print(f"  scout failed {p}: {e}")
    if not scouts:
        raise RuntimeError("no scannable clips")

    # best window per role across clips — prefer clips not used yet, so a
    # multi-clip stitch really uses several clips instead of one
    role_win = {}
    used_clips = set()
    for role in ("money", "action", "action2", "calm", "scenic", "scenic2"):
        cands = []
        for sc in scouts:
            w = sc["wins"][role]
            if w[1] - w[0] < 2.0:
                continue
            cands.append((sc, w))
        if not cands:
            role_win[role] = None
            continue
        fresh = [c for c in cands if c[0]["path"] not in used_clips]
        pool = fresh or cands
        best = max(pool, key=lambda c: c[1][1] - c[1][0])
        used_clips.add(best[0]["path"])
        role_win[role] = best

    # display-time boundaries before snapping
    bounds, cur = [0.0], 0.0
    for s in segs:
        cur += s["dur"]
        bounds.append(cur)
    money_i = next(i for i, s in enumerate(segs) if s["role"] == "money")

    # place the track drop at the money-shot start
    money_start = bounds[money_i]
    music_start = max(0.0, track["drop_estimate"] - money_start)
    if music_start + D + 0.5 > track["duration"]:
        music_start = max(0.0, track["duration"] - D - 0.5)

    # snap every boundary to the nearest beat (the Siruma signature)
    snapped = [0.0]
    for j, b in enumerate(bounds[1:], 1):
        if j == len(bounds) - 1:      # outro end stays exactly at D
            snapped.append(D)
            continue
        mt = b + music_start
        if beats:
            cand = min(beats, key=lambda x: abs(x - mt))
            d = cand - mt
            b = b + d if abs(d) <= 0.45 else b
        snapped.append(min(max(b, snapped[-1] + 0.15), D))

    # enforce minimum durations (push boundaries right, steal from money)
    mins = [s["min"] for s in segs]
    for i in range(1, len(snapped) - 1):
        need = snapped[i - 1] + mins[i - 1]
        if snapped[i] < need:
            snapped[i] = need
    snapped[-1] = max(snapped[-1], snapped[-2] + mins[-1])

    # align money start + breakdown with the track's own sections if close
    secs = energy_sections(track_name, track)
    window_secs = [r for r in secs if r[0] + music_start < music_start + D and r[1] > music_start]
    calm_starts = [r[0] - music_start for r in window_secs if r[2] == "calm"]
    peak_starts = [r[0] - music_start for r in window_secs if r[2] == "peak"]
    b_calm = next(i for i, s in enumerate(segs) if s["role"] == "calm")
    for cand in calm_starts:
        if abs(cand - snapped[b_calm]) < 4.5:
            snapped[b_calm] = max(snapped[b_calm - 1] + mins[b_calm - 1], cand)
            break
    for cand in peak_starts:
        if abs(cand - snapped[money_i]) < 5.0:
            snapped[money_i] = max(snapped[money_i - 1] + mins[money_i - 1],
                                   min(cand, snapped[money_i + 1] - mins[money_i]))
            break

    # build shots from segments
    shots, notes = [], []
    used = {}   # role -> (clip, start, end) to avoid heavy reuse
    for i, s in enumerate(segs):
        t0, t1 = snapped[i], snapped[i + 1]
        disp = t1 - t0
        if s["kind"] in ("black", "noise"):
            shots.append({"kind": s["kind"], "dur": round(disp, 3), "note": s["role"]})
            notes.append(f"{s['role']}: {'flash' if s['kind']=='black' else 'glitch'} {disp:.2f}s")
            continue
        if s["kind"] == "texture":
            mw = role_win["money"]
            sc, w = mw if mw else (scouts[0], (scouts[0]["duration"] * 0.5, scouts[0]["duration"] * 0.7))
            wl = w[1] - w[0]
            frac = {("burst1"): 0.08, ("burst2"): 0.5, ("burst3"): 0.85}[s["role"]]
            st = min(w[0] + frac * max(wl - 1.0, 0.5), w[1] - disp - 0.1)
            st = max(w[0], st)
            shots.append({"kind": "texture", "clip": sc["path"], "zoom": 2.6,
                          "start": round(st, 3), "end": round(st + disp, 3),
                          "speed": 1.0, "note": f"{s['role']} texture cutaway"})
            notes.append(f"{s['role']}: texture close-up {disp:.2f}s from money zone")
            continue
        # regular clip
        rw = role_win.get(s["role"])
        if rw is None:
            rw = (scouts[0], (0.0, scouts[0]["duration"]))
        sc, w = rw
        wl = w[1] - w[0]
        st = w[0] + max(0.0, (wl - disp) / 2)
        st = min(st, max(sc["duration"] - disp, 0))
        shots.append({"clip": sc["path"], "start": round(st, 3), "end": round(st + disp, 3),
                      "speed": 1.0, "note": s["role"]})
        notes.append(f"{s['role']}: {disp:.2f}s @ {st:.1f}s in {os.path.basename(sc['path'])}")

    total = sum(x.get("dur", 0) if x.get("kind") in ("black", "noise")
                else (x["end"] - x["start"]) / x.get("speed", 1.0) for x in shots)

    # overlays: dark intro card, one brand word pop in the money hold, URL outro
    intro_dur = snapped[1]
    money_start_d = snapped[money_i]
    money_end_d = snapped[money_i + 1]
    words = None
    try:
        brand = json.load(open(os.path.join(ROOT, "branding", "brand.json")))
        words = list(brand["taglines"]["words"]) + list(brand["taglines"].get("alt", []))
    except Exception:
        words = ["ADRENALINE", "ADVENTURE"]
    import random
    word = random.choice(words)
    w_start = min(money_start_d + 1.0, money_end_d - 3.0)
    overlays = [
        {"kind": "intro_dark", "start": 0.0, "end": round(intro_dur, 3)},
        {"kind": "word", "text": word, "start": round(w_start, 3),
         "end": round(min(w_start + 3.0, money_end_d), 3)},
        {"kind": "outro_url", "start": round(snapped[-2], 3), "end": round(total, 3)},
    ]
    return {"shots": shots, "overlays": overlays,
            "notes": {"structure": notes, "music_start": round(music_start, 3),
                      "bpm": track["bpm"], "style": "siruma",
                      "sections_used": window_secs}}
