"""
gen_fx.py - AI & procedural visual effects assets for the pipeline.

Modes
-----
1. Local procedural (free, offline):
       python tools\\gen_fx.py make            # generate all built-in FX
       python tools\\gen_fx.py make embers     # one FX only
   Built-ins: embers, flare, light_leak, speedlines
   All FX render as RGBA .mov clips with alpha = glow/intensity, built to be
   screen-blended (fire, sparks, light) over footage.

2. Wan-AI/Wan2.1-T2V-14B via Replicate (needs REPLICATE_API_TOKEN):
       set REPLICATE_API_TOKEN=r8_...
       python tools\\gen_fx.py wan "a slow-motion burst of sparks and embers" \\
           --size 720p --out assets\\fx\\spark_burst.mp4
   Generates 4-5s 480p/720p clips (silent). Costs ~$0.50-1.00 per clip.
   Model: wavespeedai/wan-2.1-t2v-480p | -720p  (14B) OR wan-video/wan-2.1-1.3b

3. List assets:
       python tools\\gen_fx.py list
"""
import argparse, json, os, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = os.path.join(ROOT, "tools", "ffmpeg", "ffmpeg-9.0.2-essentials_build", "bin", "ffmpeg.exe")
FX_DIR = os.path.join(ROOT, "assets", "fx")

# ----------------------------------------------------------------- procedural FX
# Each FX is built as alpha = glow intensity so overlay (NOT blend) composites
# it like an additive light effect. 1920x1080 @30fps, 6s.
# Each value = a complete -filter_complex graph with its own lavfi sources,
# ending in an RGBA stream.
PROCEDURAL = {
    "embers": (
        "color=c=0xffa030:s=1920x2160:r=30:d=6,format=rgb24[base];"
        "color=c=black:s=1920x2160:r=30:d=6,format=gray,"
        "geq=lum='if(gt(random(1),0.99),255,0)',gblur=sigma=1.2,"
        "geq=lum='clip((lum(X,Y)-14)*14,0,255)'[m1];"
        "color=c=black:s=1920x2160:r=30:d=6,format=gray,"
        "geq=lum='if(gt(random(3),0.9965),255,0)',gblur=sigma=4.5,"
        "geq=lum='clip((lum(X,Y)-12)*8,0,255)'[m2];"
        "[m1][m2]blend=all_mode=lighten[mask];"
        "[base][mask]alphamerge,crop=1920:1080:0:'max(0,1080-n/30*190)',"
        "fade=t=in:st=0:d=0.5:alpha=1,fade=t=out:st=5.2:d=0.8:alpha=1"
    ),
    "flare": (
        "color=c=black:s=1920x1080:r=30:d=6,"
        "geq=r='255':g='235':b='205':a='min(255,235*exp(-(hypot(X-640-80*T,Y-470+55*T)/70))"
        "+150*exp(-(abs(Y-470+55*T)/13)-(abs(X-640-80*T)/420)))',"
        "fade=t=in:st=0:d=0.5:alpha=1,fade=t=out:st=5.0:d=1.0:alpha=1,format=rgba"
    ),
    "light_leak": (
        "color=c=black:s=1920x1080:r=30:d=6,"
        "geq=r='255':g='105':b='28':a='min(230,235*exp(-(hypot(X-150-330*T,Y-540)/330)))',"
        "fade=t=in:st=0:d=0.8:alpha=1,fade=t=out:st=4.6:d=1.4:alpha=1,format=rgba"
    ),
    "speedlines": (
        "color=c=black:s=1920x1080:r=30:d=6,"
        "geq=r='255':g='255':b='255':"
        "a='210*pow(abs(sin(atan2(Y-540,X-960)*18)),14)*max(0,1-hypot(X-960,Y-540)/1150)',"
        "fade=t=in:st=0:d=0.25:alpha=1,fade=t=out:st=5.0:d=1.0:alpha=1,format=rgba"
    ),
}


def make_procedural(names=None):
    os.makedirs(FX_DIR, exist_ok=True)
    wanted = names or list(PROCEDURAL)
    for name in wanted:
        fc = PROCEDURAL.get(name)
        if fc is None:
            print(f"unknown FX '{name}' (choose from {', '.join(PROCEDURAL)})"); continue
        out = os.path.join(FX_DIR, f"{name}.mov")
        cmd = [FFMPEG, "-y", "-filter_complex", fc,
               "-c:v", "qtrle", out]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            print(f"FAILED {name}: {p.stderr[-500:]}"); continue
        print(f"  fx: {os.path.relpath(out, ROOT)}")
    print("done.")


# ----------------------------------------------------------------- Wan-AI via Replicate
WAN_MODELS = {
    "480p": "wavespeedai/wan-2.1-t2v-480p",
    "720p": "wavespeedai/wan-2.1-t2v-720p",
    "1.3b": "wan-video/wan-2.1-1.3b",
}


def wan_generate(prompt, size, out_name, seed=None):
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("REPLICATE_API_TOKEN not set.")
        print("  1) make an account at https://replicate.com")
        print("  2) set it:  setx REPLICATE_API_TOKEN \"r8_...\"  (restart terminal)")
        print("  3) re-run this command")
        return 1
    model = WAN_MODELS[size]
    body = {"input": {"prompt": prompt}}
    if seed is not None:
        body["input"]["seed"] = seed
    req = urllib.request.Request(
        f"https://api.replicate.com/v1/models/{model}/predictions",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "Prefer": "wait=60"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            pred = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API error {e.code}: {e.read().decode()[:500]}"); return 1

    cid = pred.get("id")
    status, output = pred.get("status"), pred.get("output")
    print(f"prediction {cid}: {status}")
    while status not in ("succeeded", "failed", "canceled"):
        time.sleep(6)
        with urllib.request.urlopen(
                urllib.request.Request(f"https://api.replicate.com/v1/predictions/{cid}",
                                       headers={"Authorization": f"Bearer {token}"}),
                timeout=60) as r:
            pred = json.loads(r.read().decode())
        status, output = pred.get("status"), pred.get("output")
        print(f"  ... {status}")
    if status != "succeeded":
        print(f"generation {status}: {pred.get('error')}"); return 1

    url = output if isinstance(output, str) else (output or [None])[0]
    os.makedirs(FX_DIR, exist_ok=True)
    out = out_name if os.path.isabs(out_name) else os.path.join(FX_DIR, out_name)
    print(f"downloading -> {out}")
    urllib.request.urlretrieve(url, out)
    print("done. Add it to a plan: {\"fx\": [{\"file\": ..., \"start\": 44.5, \"end\": 49.5, \"opacity\": 0.8}]}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make", help="generate local procedural FX")
    mk.add_argument("names", nargs="*", help="fx to build (default: all)")
    wn = sub.add_parser("wan", help="generate a Wan2.1-T2V-14B clip via Replicate API")
    wn.add_argument("prompt")
    wn.add_argument("--size", choices=list(WAN_MODELS), default="480p")
    wn.add_argument("--out", default="wan_fx.mp4")
    wn.add_argument("--seed", type=int, default=None)
    sub.add_parser("list", help="list available FX assets")
    args = ap.parse_args()

    if args.cmd == "make":
        make_procedural(args.names or None)
    elif args.cmd == "wan":
        return wan_generate(args.prompt, args.size, args.out, args.seed)
    else:
        if os.path.isdir(FX_DIR):
            for f in sorted(os.listdir(FX_DIR)):
                print(f"  {f}")
        else:
            print("no assets/fx yet - run: python tools\\gen_fx.py make")
    return 0


if __name__ == "__main__":
    sys.exit(main())
