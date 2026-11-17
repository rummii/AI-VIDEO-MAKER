"""
make_video.py - the edit engine for the action-sports video pipeline.

Two steps, run by the agent (not you):

  1) analyze   : probe every clip in clips/ and extract preview frames
                 so the agent can watch the footage and pick the best moments.
  2) build     : take a shot list (JSON the agent writes after watching frames),
                 a music track, target length and formats; cut on the beat,
                 reframe, color-punch, loudness-normalize and render.

Usage:
  python tools/make_video.py analyze
  python tools/make_video.py build --shots tools/edits/<name>.shots.json
         [--music "<file or part of name>"] [--format both|9:16|16:9]
         [--out output/<name>]
"""
import argparse, json, os, subprocess, sys, glob, math, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand_overlays

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = os.path.join(ROOT, "tools", "ffmpeg", "ffmpeg-9.0.2-essentials_build", "bin", "ffmpeg.exe")
FFPROBE = os.path.join(ROOT, "tools", "ffmpeg", "ffmpeg-9.0.2-essentials_build", "bin", "ffprobe.exe")
CLIPS = os.path.join(ROOT, "clips")
MUSIC_DIR = os.path.join(ROOT, "music")
LIB = os.path.join(MUSIC_DIR, "library.json")
EDITS = os.path.join(ROOT, "tools", "edits")
FRAMES = os.path.join(ROOT, "tools", "frames")

VIDEO_EXT = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".mts", ".m2ts", ".wmv", ".3gp")

# ---------------------------------------------------------------- helpers
def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", **kw)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{p.stderr[-2000:]}")
    return p.stdout

def probe(path):
    j = json.loads(run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", path]))
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise RuntimeError(f"no video stream in {path}")
    fps = eval(v.get("r_frame_rate", "30/1"))
    dur = float(j["format"].get("duration") or v.get("duration") or 0)
    return {
        "file": path,
        "name": os.path.basename(path),
        "width": v["width"], "height": v["height"],
        "fps": round(fps, 3), "duration": round(dur, 3),
        "has_audio": any(s["codec_type"] == "audio" for s in j["streams"]),
    }

# ---------------------------------------------------------------- analyze
def cmd_analyze(args):
    os.makedirs(FRAMES, exist_ok=True)
    clips = [p for p in glob.glob(os.path.join(CLIPS, "*"))
             if os.path.splitext(p)[1].lower() in VIDEO_EXT]
    if not clips:
        print("No clips found in clips/ - drop your raw footage there first.")
        return 1
    report = []
    for path in sorted(clips):
        info = probe(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        fdir = os.path.join(FRAMES, stem)
        os.makedirs(fdir, exist_ok=True)
        n = 10
        step = max(info["duration"] / (n + 1), 0.5)
        for i in range(n):
            t = step * (i + 1)
            outjpg = os.path.join(fdir, f"t{t:07.2f}.jpg")
            run([FFMPEG, "-y", "-ss", str(t), "-i", path, "-frames:v", "1",
                 "-vf", "scale=640:-2", "-q:v", "3", outjpg])
        report.append(info)
        print(f"analyzed {info['name']}: {info['width']}x{info['height']} "
              f"{info['duration']:.1f}s {info['fps']}fps -> {len(glob.glob(os.path.join(fdir, '*.jpg')))} frames in tools/frames/{stem}/")
    os.makedirs(EDITS, exist_ok=True)
    with open(os.path.join(EDITS, "clips_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("\nNext: agent reviews frames, writes a shot list JSON, then runs build.")
    return 0

# ---------------------------------------------------------------- music
def pick_track(query=None, need=20.0):
    lib = json.load(open(LIB))
    if query:
        for name, d in lib.items():
            if query.lower() in name.lower():
                return name, d
        print(f"no track matching '{query}', picking automatically")
    # for a short edit prefer tracks whose first drop is early
    scored = sorted(lib.items(), key=lambda kv: abs(kv[1]["drop_estimate"] - need * 0.35))
    name, d = scored[0]
    return name, d

def beat_schedule(track, start, length, heavy=True):
    """Return list of cut times (absolute in the track) covering `length` seconds.
    Cut spacing follows the music: every 2 beats when heavy, every 4 otherwise."""
    beats = [b for b in track["beats"] if b >= start]
    if not beats:
        beats = [start]
    cuts = []
    i = 0
    while not cuts or cuts[-1] - cuts[0] < length:
        step = 2 if heavy else 4
        idx = min(i * step, len(beats) - 1)
        t = beats[idx]
        if cuts and t <= cuts[-1]:
            break
        cuts.append(t)
        i += 1
    return cuts

def choose_music_segment(track, length, hit_drop_at=0.45):
    """Start the music so a drop hits ~45% through the edit; fall back to max energy."""
    dur = track["duration"]
    drop = track["drop_estimate"]
    start = max(0.0, drop - length * hit_drop_at)
    if start + length + 1 > dur:          # not enough tail; start from top
        start = max(0.0, dur - length - 1)
    return round(start, 3)

# ---------------------------------------------------------------- build
def build_filter(shots, out_w, out_h, fps, music_start, overlays=None, fade_out=0.8,
                 sfx_list=None):
    """Assemble trim/speed/scale/color filters + concat + brand overlays.
    SFX (risers/impacts) are mixed into the music before loudnorm.
    Shot kinds: "clip" (default; file input), "texture" (file input, zoomed
    crop for B-roll bridges), "black" (flash card), "noise" (glitch static).
    Returns (filter, inputs_extra, total). inputs_extra is a list of extra
    input args (music + overlay images) appended after the clip inputs."""
    parts, labels = [], []
    file_idx = 0
    for i, s in enumerate(shots):
        kind = s.get("kind", "clip")
        if kind == "black":
            parts.append(f"color=c=black:s={out_w}x{out_h}:r={fps}:d={s['dur']:.3f},"
                         f"setsar=1,format=yuv420p[v{i}]")
        elif kind == "noise":
            parts.append(f"color=c=gray:s={out_w}x{out_h}:r={fps}:d={s['dur']:.3f},"
                         f"noise=alls=100:allf=t+u,eq=contrast=1.7:saturation=0,"
                         f"setsar=1,format=yuv420p[v{i}]")
        else:
            speed = s.get("speed", 1.0)
            trim = f"[{file_idx}:v]trim=start={s['start']:.3f}:end={s['end']:.3f},setpts=(PTS-STARTPTS)/{speed}"
            file_idx += 1
            if kind == "texture":
                z = s.get("zoom", 2.6)
                chain = (f",fps={fps},crop=iw/{z:.2f}:ih/{z:.2f},"
                         f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                         f"crop={out_w}:{out_h},eq=contrast=1.12:saturation=1.3,"
                         f"setsar=1,format=yuv420p")
            else:
                # normalize fps first so concat works across mixed sources
                chain = f",fps={fps},scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h}"
                color = ",eq=contrast=1.06:saturation=1.22:gamma=1.03,unsharp=5:5:0.6:5:5:0.0,setsar=1"
                chain += color
            parts.append(f"{trim}{chain}[v{i}]")
        labels.append(f"[v{i}]")
    concat = "".join(labels) + f"concat=n={len(shots)}:v=1:a=0[vcat]"
    # audio: cut music segment, mix in SFX (risers/impacts), normalize, fade
    total = sum(s["dur"] if s.get("kind") in ("black", "noise")
                else (s["end"] - s["start"]) / s.get("speed", 1.0) for s in shots)
    music_idx = file_idx
    sfx = (sfx_list or [])
    # input order: clips, music, sfx..., overlay images...
    sfx_base = music_idx + 1
    amix_inputs = f"[amusic]" + "".join(f"[asfx{j}]" for j in range(len(sfx)))
    a = (f"[{music_idx}:a]atrim=start={music_start:.3f}:duration={total:.3f},"
         f"asetpts=PTS-STARTPTS,volume=1.0[amusic]")
    parts.append(a)
    for j, e in enumerate(sfx):
        idx = sfx_base + j
        gain = float(e.get("gain_db", 0.0))
        at = max(0.0, min(float(e.get("start", 0.0)), total))
        parts.append(f"[{idx}:a]adelay={int(at*1000)}|{int(at*1000)},"
                     f"asetpts=PTS-STARTPTS,volume={10**(gain/20):.3f}[asfx{j}]")
    if sfx:
        parts.append(f"{amix_inputs}amix=inputs={len(sfx)+1}:duration=longest:"
                     f"normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,"
                     f"afade=t=out:st={max(total - 1.0, 0):.3f}:d=1.0[aout]")
    else:
        parts.append(f"[amusic]loudnorm=I=-14:TP=-1.5:LRA=11,"
                     f"afade=t=out:st={max(total - 1.0, 0):.3f}:d=1.0[aout]")
    parts.append(concat)
    extra_inputs = []
    # SFX inputs follow music + overlay images
    for e in sfx:
        extra_inputs += ["-i", e["file"]]
    current = "[vcat]"
    if overlays:
        for k, ov in enumerate(overlays):
            img_idx = music_idx + 1 + len(sfx) + k
            extra_inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", ov["png"]]
            if ov["mode"] == "watermark":
                chain = (f"[{img_idx}:v]format=rgba[ov{k}]")
                x = f"main_w-overlay_w-main_w*{brand_margin()}"
                y = f"main_h*{brand_margin()}"
                ovf = f"{current}[ov{k}]overlay={x}:{y}:eof_action=pass[vw{k}]"
            else:
                s, e = ov["start"], ov["end"]
                fd = min(0.4, (e - s) / 3)
                chain = (f"[{img_idx}:v]format=rgba,"
                         f"fade=t=in:st={s:.3f}:d={fd:.3f}:alpha=1,"
                         f"fade=t=out:st={max(e - fd, s):.3f}:d={fd:.3f}:alpha=1[ov{k}]")
                ovf = f"{current}[ov{k}]overlay=0:0:eof_action=pass[vw{k}]"
            parts.append(chain)
            parts.append(ovf)
            current = f"[vw{k}]"
        final = current
    else:
        final = current
    if fade_out > 0:
        parts.append(f"{final}fade=t=out:st={max(total - fade_out, 0):.3f}:d={fade_out:.3f}[vout]")
        final = "[vout]"
    return ";".join(parts), extra_inputs, total, final

def brand_margin():
    return 0.03

def cmd_build(args):
    shots_doc = json.load(open(args.shots))
    shots = shots_doc["shots"]
    fmt = args.format
    if fmt not in ("9:16", "16:9", "both", "16:9-4k", "9:16-4k"):
        print("format must be 9:16, 16:9, both, 16:9-4k or 9:16-4k"); return 1
    track_name, track = pick_track(args.music)
    print(f"music: {track_name} ({track['bpm']} BPM)")
    for s in shots:
        speed = s.get("speed", 1.0)
        if speed != 1.0 and not (0.25 <= speed <= 4):
            print(f"bad speed {speed}"); return 1

    total = sum(s.get("dur", 0) if s.get("kind") in ("black", "noise")
                else (s["end"] - s["start"]) / s.get("speed", 1.0) for s in shots)
    # siruma plans pre-place the music so the drop hits the money shot
    music_start = shots_doc.get("music_start")
    if music_start is None:
        music_start = choose_music_segment(track, total)
    music_start = max(0.0, min(float(music_start), max(track["duration"] - total - 0.5, 0.0)))
    do_brand = not args.nobrand and os.path.exists(os.path.join(ROOT, "branding", "brand.json"))

    # sponsor logos: "auto" = everything in sponsors/, or comma-separated paths
    sponsor_files = None
    if do_brand and getattr(args, "sponsors", None):
        if args.sponsors.strip().lower() == "auto":
            sdir = os.path.join(ROOT, "sponsors")
            if os.path.isdir(sdir):
                sponsor_files = sorted(os.path.join(sdir, f) for f in os.listdir(sdir)
                                       if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
        else:
            sponsor_files = [p.strip() for p in args.sponsors.split(",") if p.strip()]
        if sponsor_files:
            print(f"sponsor logos: {len(sponsor_files)}")

    fps = 30
    if fmt == "both":
        formats = ["9:16", "16:9"]
    else:
        formats = [fmt]
    out_base = os.path.splitext(os.path.basename(args.out))[0]
    project = out_base
    for f in formats:
        w, h = {"9:16": (1080, 1920), "16:9": (1920, 1080),
                "16:9-4k": (3840, 2160), "9:16-4k": (2160, 3840)}[f]
        suffix = f.replace(":", "x").replace("-", "_")
        inputs = []
        for s in shots:
            if s.get("kind") in ("black", "noise"):
                continue        # generated inside the filter graph
            inputs += ["-i", s["clip"]]
        # music last
        mpath = os.path.join(MUSIC_DIR, track_name)
        inputs += ["-i", mpath]
        overlays = None
        if do_brand:
            overlays = brand_overlays.build_overlay_plan(
                project, shots, total, w, h, shots_doc.get("overlays"),
                sponsors=sponsor_files)
        # SFX inserts: shots.json "sfx" -> [{file, start, gain_db?}]
        sfx_list = shots_doc.get("sfx", [])
        resolved_sfx = []
        for e in sfx_list:
            f = e["file"]
            if not os.path.isabs(f):
                f = os.path.join(ROOT, f)
            if not os.path.exists(f):
                print(f"sfx missing (skipped): {f}")
                continue
            resolved_sfx.append(dict(e, file=f))
        sfx_list = resolved_sfx
        if sfx_list:
            print(f"sfx: {len(sfx_list)} inserts")
        filt, extra_inputs, total, vfinal = build_filter(
            shots, w, h, fps, music_start, overlays, sfx_list=sfx_list)
        inputs += extra_inputs
        out = args.out.replace(":16:9", "").replace(":9:16", "") or out_base
        outpath = os.path.join(ROOT, "output", f"{out_base}_{suffix}.mp4")
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        cmd = [FFMPEG, "-y"] + inputs + [
            "-filter_complex", filt,
            "-map", vfinal, "-map", "[aout]",
            "-c:v", "libx264", "-crf", "20", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", outpath,
        ]
        print(f"rendering {os.path.basename(outpath)} ({w}x{h}, {total:.1f}s, drop@~{music_start + total*0.45:.1f}s"
              f"{', branded' if overlays else ''})...")
        run(cmd)
        print(f"  done -> {outpath}")
    return 0

# ---------------------------------------------------------------- auto (Siruma style)
def cmd_auto(args):
    import edit_style
    D = args.duration
    if not (15 <= D <= 120):
        print("duration must be 15-120 seconds"); return 1
    clips = [c.strip() for c in args.clip.split(",") if c.strip()]
    for c in clips:
        if not os.path.exists(c):
            print(f"clip not found: {c}"); return 1
    track_name, track = pick_track(args.music)
    print(f"music: {track_name} ({track['bpm']} BPM) | style: siruma | target {D:.0f}s")
    print("scouting footage...")
    plan = edit_style.build_plan(clips, track_name, track, D, seed=args.seed)
    doc = {
        "name": os.path.splitext(os.path.basename(args.out))[0],
        "source": clips,
        "style": "siruma",
        "music_start": plan["notes"]["music_start"],
        "notes": "\n".join(plan["notes"]["structure"]),
        "shots": plan["shots"],
        "overlays": plan["overlays"],
    }
    os.makedirs(EDITS, exist_ok=True)
    jpath = os.path.join(EDITS, f"{doc['name']}.shots.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"plan written -> {jpath}")
    for n in plan["notes"]["structure"]:
        print(f"  {n}")
    if args.plan_only:
        return 0
    args.shots = jpath
    # pin the EXACT track the plan was scored against — otherwise the build
    # would re-roll its own random pick and break every beat snap
    args.music = track_name
    return cmd_build(args)

# ---------------------------------------------------------------- stitch (footage folder)
DEFAULT_MUSIC_POOL = [
    "Uncan - Lazy Sunday.mp3",
    "Troigo - Bacetti.mp3",
    "Uncan - Harx Hitter.mp3",
    "Stirquoise - River Ship.mp3",
    "John Bartmann - Panama Lounge.mp3",
    "Troigo - Motor On.mp3",
    "Troigo - Taking In The Moment.mp3",
]

def cmd_stitch(args):
    """Auto-stitch every clip in a folder into one branded Siruma-style edit."""
    import edit_style, glob
    D = args.duration
    if not (15 <= D <= 120):
        print("duration must be 15-120 seconds"); return 1
    folder = os.path.join(ROOT, args.dir)
    if not os.path.isdir(folder):
        print(f"folder not found: {folder}"); return 1
    exts = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm")
    clips = sorted(os.path.join(folder, f) for f in os.listdir(folder)
                   if f.lower().endswith(exts))
    if not clips:
        print(f"no video files in {folder} (drop clips there first)"); return 1
    print(f"stitching {len(clips)} clip(s) from {os.path.relpath(folder, ROOT)}:")
    for c in clips:
        print(f"  - {os.path.basename(c)}")

    music = args.music
    if not music:
        import random as _r
        if args.seed is not None:
            _r.seed(args.seed)
        music = _r.choice(DEFAULT_MUSIC_POOL)
        music = os.path.splitext(music)[0]
        print(f"music: auto-picked '{music}' (use --music to choose, --seed to repeat)")
    track_name, track = pick_track(music)
    print(f"music: {track_name} ({track['bpm']} BPM) | style: siruma | target {D:.0f}s")
    print("scouting footage...")
    plan = edit_style.build_plan(clips, track_name, track, D, seed=args.seed)
    doc = {
        "name": os.path.splitext(os.path.basename(args.out))[0],
        "source": clips,
        "style": "siruma",
        "music_start": plan["notes"]["music_start"],
        "notes": "\n".join(plan["notes"]["structure"]),
        "shots": plan["shots"],
        "overlays": plan["overlays"],
    }
    os.makedirs(EDITS, exist_ok=True)
    jpath = os.path.join(EDITS, f"{doc['name']}.shots.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"plan written -> {jpath}")
    for n in plan["notes"]["structure"]:
        print(f"  {n}")
    if args.plan_only:
        return 0
    args.shots = jpath
    args.music = track_name
    return cmd_build(args)

# ---------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("analyze")
    b = sub.add_parser("build")
    b.add_argument("--shots", required=True)
    b.add_argument("--music", default=None)
    b.add_argument("--format", default="both")
    b.add_argument("--out", required=True)
    b.add_argument("--nobrand", action="store_true")
    b.add_argument("--sponsors", default=None, help="'auto' or comma-separated logo paths")
    a = sub.add_parser("auto")
    a.add_argument("--clip", required=True, help="source clip(s), comma-separated")
    a.add_argument("--music", default=None)
    a.add_argument("--duration", type=float, default=40.0)
    a.add_argument("--format", default="both")
    a.add_argument("--out", required=True)
    a.add_argument("--seed", type=int, default=None)
    a.add_argument("--plan-only", action="store_true")
    a.add_argument("--nobrand", action="store_true")
    a.add_argument("--sponsors", default=None, help="'auto' or comma-separated logo paths")
    s = sub.add_parser("stitch", help="auto-stitch every clip in a folder into one edit")
    s.add_argument("--dir", default="footage", help="folder of clips (default: footage)")
    s.add_argument("--music", default=None, help="track name, or omit for auto-pick")
    s.add_argument("--duration", type=float, default=60.0)
    s.add_argument("--format", default="both")
    s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int, default=None)
    s.add_argument("--plan-only", action="store_true")
    s.add_argument("--nobrand", action="store_true")
    s.add_argument("--sponsors", default=None, help="'auto' or comma-separated logo paths")
    args = ap.parse_args()
    if args.cmd == "analyze":
        sys.exit(cmd_analyze(args))
    elif args.cmd == "auto":
        sys.exit(cmd_auto(args))
    elif args.cmd == "stitch":
        sys.exit(cmd_stitch(args))
    else:
        sys.exit(cmd_build(args))

if __name__ == "__main__":
    main()
