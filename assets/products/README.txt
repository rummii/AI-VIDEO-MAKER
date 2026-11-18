Product photos for AI object swaps (e.g. putting exact sneakers on a passenger).

Drop a PNG/JPG here, ideally:
- product filling the frame, side or 3/4 view
- plain/light background
- under 256 KB (the tool embeds images as base64 data URIs)

Then:

    setx REPLICATE_API_TOKEN "r8_..."
    (restart terminal)

    python tools\video_swap.py --video clips\IMG_3730.MP4 --start 6 --duration 8 ^
      --ref assets\products\your_sneaker.png ^
      --prompt "Replace the passenger's slippers with the exact sneakers in the reference image, matching lighting and perspective" ^
      --out assets\edits\launch_sneakers.mp4

The edited segment comes out at assets\edits\launch_sneakers.mp4. Splice it
back into the source or reference it directly as a shot in a shots.json plan.
