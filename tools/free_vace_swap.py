"""Free VACE Fast Space test: reference-video + product photo -> edited video."""
import os, sys, shutil
from gradio_client import Client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    clip = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "assets/edits/_swap_segment.mp4")
    ref = os.path.join(ROOT, sys.argv[2] if len(sys.argv) > 2 else "assets/products/sneaker.png")
    out = os.path.join(ROOT, sys.argv[3] if len(sys.argv) > 3 else "assets/edits/vace_swap_test.mp4")
    prompt = ("Replace the passenger's slippers with the black sneakers with silver stripes "
              "shown in the reference image, matching lighting and perspective. "
              "Keep the person, clothing, background and motion unchanged.")
    print("connecting...", flush=True)
    c = Client("linoyts/wan2-1-VACE-fast", verbose=False)
    gallery = [
        {"video": {"path": clip}, "caption": "source video"},
        {"image": {"path": ref}, "caption": "sneakers to use"},
    ]
    print("submitting (this may queue on ZeroGPU)...", flush=True)
    result = c.predict(
        gallery_images=gallery,
        mode="Reference",
        prompt=prompt,
        height=512,
        width=832,
        negative_prompt="blurry, distorted, extra limbs, bad quality, watermark, text",
        duration_seconds=3.0,
        guidance_scale=1.0,
        steps=6,
        seed=42,
        randomize_seed=False,
        remove_bg=False,
        api_name="/generate_video",
    )
    print("result:", result, flush=True)
    video = result[0] if isinstance(result, (list, tuple)) else result
    if video:
        shutil.copy(video["video"] if isinstance(video, dict) else video, out)
        print("saved ->", out, flush=True)

if __name__ == "__main__":
    main()
