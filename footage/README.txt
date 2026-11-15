Drop clips in this folder for automatic stitching into a single branded video.
==============================================================================

How it works
------------
Run:

    python tools\make_video.py stitch --duration 60 --format both --out output\my_edit

The stitcher scans EVERY video file in this folder (mp4, mov, m4v, avi, mkv,
webm), scouts each one (motion + color scoring), then builds one Siruma-style
edit drawing the best window from ANY clip for each role — action scenes,
scenic cutaways, calm beat, money shot — all cut on the music's beat grid.

Ordering
--------
Clips are processed in alphabetical filename order. To control the order
(and which clips win roles), prefix filenames:

    01_beach.mp4
    02_launch.mp4
    03_sunset.mp4

You don't have to — order only affects tie-breaks; the scout picks the best
material for each slot regardless.

Music
-----
- Omit --music and the stitcher auto-picks a track from the brand-default
  pool (chill house / indie dance, all commercial-safe).
- Or name one:  --music "River Ship"     (see music\library.json)
- Add --seed 7 to reproduce the exact same auto pick again.

Tips
----
- More clips = more variety; 3-8 clips is the sweet spot for a 60s edit.
- Mixed resolutions, frame rates, and orientations are fine.
- Vertical clips in a 16:9 render are center-cropped; use 9:16 or 16:9
  output that matches the majority of your footage.
- The plan is written to tools\edits\<name>.shots.json — edit it and re-run
  `build` to hand-tune any window.
