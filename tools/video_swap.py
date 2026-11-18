"""
video_swap.py - Hosted object swap in video (e.g. slippers -> sneakers).

Uses Replicate's official Wan 2.7 VideoEdit model:
  https://replicate.com/wan-video/wan-2.7-videoedit

Why hosted: this laptop has no GPU and ~7.7GB RAM, so VACE/Wan editing models
cannot run locally. Wan 2.7 VideoEdit on Replicate supports prompt-based edits
with an optional product reference image, preserving motion/audio.

Cost: roughly $0.10 per second of OUTPUT video (10s cap per prediction).

SETUP (one time):
  1. Make an account at https://replicate.com
  2. Create a token: https://replicate.com/account/api-tokens
  3. setx REPLICATE_API_TOKEN "r8_..."   (then restart the terminal)
  4. Put a photo of the exact sneakers in assets/products/ (white background,
     side view, under 256KB is ideal)

USAGE:
  python tools\\video_swap.py --video clips/IMG_3730.MP4 --start 6 --duration 8 \\
      --ref assets/products/mg_sneaker.png \\
      --prompt "Replace the passenger's slippers with the exact sneakers shown in the reference image, matching lighting and perspective" \\
      --out assets/edits/launch_sneakers.mp4

The tool extracts the segment, compresses it to a data URI (<1MB), submits the
prediction, polls until done, and downloads the edited MP4. Then either:
  - use the edited clip directly as a shot in a shots.json plan, or
  - splice it back into the full footage with ffmpeg before re-cutting.
"""
import argparse, base64, json, os, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = os.path.join(ROOT, "tools", "ffmpeg", "ffmpeg-9.0.2-essentials_build", "bin", "ffmpeg.exe")
MODEL = "wan-video/wan-2.7-videoedit"
API = "https://api.replicate.com/v1/models/" + MODEL + "/predictions"
LIMIT = 950_000   # data URI payload budget (~1MB)


def data_uri(path, mime):
    raw = open(path, "rb").read()
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def extract_segment(video, start, duration, out, max_bytes=LIMIT):
    """Extract a small vertical H.264 segment that fits in a data URI."""
    for scale_w, crf in ((480, 30), (360, 30), (320, 28), (288, 26)):
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-ss", str(start),
               "-i", video, "-t", str(duration),
               "-vf", f"scale={scale_w}:-2,fps=24",
               "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
               "-an", out]
        subprocess.run(cmd, check=True)
        if os.path.getsize(out) <= max_bytes:
            return out, os.path.getsize(out)
    raise RuntimeError("could not compress segment under 1MB; shorten --duration")


def api_request(method, url, token, body=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        if e.code == 402:
            print("Replicate says PAYMENT REQUIRED (402).")
            print("Add a payment method or claim free credit at:")
            print("  https://replicate.com/account/billing")
            print("Then re-run this command.")
            print("Details:", detail)
        elif e.code == 401:
            print("REPLICATE_API_TOKEN rejected (401). Create a new token at:")
            print("  https://replicate.com/account/api-tokens")
            print("Details:", detail)
        else:
            print(f"Replicate API error {e.code}: {detail}")
        raise


def swap(video, start, duration, ref, prompt, out, resolution="720p", aspect="9:16", seed=None):
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("REPLICATE_API_TOKEN is not set. Set it with:")
        print('  setx REPLICATE_API_TOKEN "r8_..."   (then restart the terminal)')
        return 1

    tmp = os.path.join(ROOT, "assets", "edits", "_swap_segment.mp4")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    clip, size = extract_segment(video, start, duration, tmp)
    print(f"segment: {clip} ({size//1024} KB)")

    payload = {
        "input": {
            "video": data_uri(clip, "video/mp4"),
            "prompt": prompt,
            "reference_image": data_uri(ref, "image/png") if ref.lower().endswith(".png")
                               else data_uri(ref, "image/jpeg"),
            "duration": int(round(duration)),
            "resolution": resolution,
            "aspect_ratio": aspect,
            "audio_setting": "origin",
        }
    }
    if seed is not None:
        payload["input"]["seed"] = seed

    print("submitting to", MODEL, "...")
    pred = api_request("POST", API, token, payload)
    pid = pred.get("id")
    print("prediction:", pid, pred.get("status"))
    get_url = pred.get("urls", {}).get("get") or f"https://api.replicate.com/v1/predictions/{pid}"

    while pred.get("status") not in ("succeeded", "failed", "canceled"):
        time.sleep(4)
        pred = api_request("GET", get_url, token)
        print("  ...", pred.get("status"))
    if pred.get("status") != "succeeded":
        print("FAILED:", pred.get("error")); return 1

    url = pred.get("output")
    if isinstance(url, list):
        url = url[0] if url else None
    if not url:
        print("no output URL in prediction"); return 1

    os.makedirs(os.path.dirname(out), exist_ok=True)
    # Replicate delivery files are public HTTPS; fall back to token if needed
    try:
        urllib.request.urlretrieve(url, out)
    except Exception:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as f:
            f.write(r.read())
    print("saved ->", out, f"({os.path.getsize(out)//1024} KB)")
    print("preview:", pred.get("urls", {}).get("web", ""))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--duration", type=float, default=8.0)
    ap.add_argument("--ref", help="product photo (sneakers/shades), PNG or JPG")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", default="assets/edits/swap.mp4")
    ap.add_argument("--resolution", choices=["720p", "1080p"], default="720p")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    return swap(args.video, args.start, args.duration, args.ref, args.prompt,
                args.out, args.resolution, args.aspect, args.seed)


if __name__ == "__main__":
    sys.exit(main())
