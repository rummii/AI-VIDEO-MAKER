"""Free video swap via Lucy Edit Dev Space using the official gradio_client."""
import os, sys
from gradio_client import Client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    video = sys.argv[1] if len(sys.argv) > 1 else "assets/edits/_swap_segment.mp4"
    prompt = sys.argv[2] if len(sys.argv) > 2 else (
        "Replace the passenger's slippers with black sneakers with silver stripes, "
        "matching lighting and perspective. Keep everything else unchanged.")
    out = sys.argv[3] if len(sys.argv) > 3 else "assets/edits/lucy_swap_test.mp4"

    print("connecting to free Space...", flush=True)
    client = Client("decart-ai/lucy-edit-dev", verbose=False)
    print("submitting 8s clip + prompt...", flush=True)
    result = client.predict(
        video_path=os.path.join(ROOT, video),
        prompt=prompt,
        negative_prompt="",
        num_frames=61,
        auto_resize=True,
        manual_height=480,
        manual_width=832,
        guidance_scale=5.0,
        api_name="/process_video",
    )
    print("result:", result, flush=True)
    if result:
        import shutil
        shutil.copy(result, os.path.join(ROOT, out))
        print("saved ->", out, flush=True)

if __name__ == "__main__":
    main()
