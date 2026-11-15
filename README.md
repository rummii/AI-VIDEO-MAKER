# Action Sports Edit Pipeline

Drop footage in `clips/`, say what you want, get finished videos in `output/`.
The agent runs everything; you never touch a command line.

## Your workflow

1. **Drop your raw clips** into the `clips/` folder (any format: mp4, mov, mts...)
2. **Tell the agent** e.g. *"make a 20s reel, something heavy"* or
   *"30-60s video for YouTube, 16:9, use DUBSTEP ATTACK 4"*
3. The agent then:
   - scans your clips and **actually watches them** (extracts frames, picks the
     best moments - bails, airs, landings)
   - picks music from `music/` (or uses a track you name) and locks every cut
     **to the beat**, with the drop hitting mid-video
   - builds the edit: hard cuts on beat, slow-mo on the money shot, speed-ups
     on filler, color punch-up, 9:16 and/or 16:9 reframe
   - renders platform-ready MP4s (H.264, loudness-normalized to -14 LUFS)
   - shows you a preview; you give notes and it re-renders

## Folders

| Folder    | What it is                                              |
|-----------|---------------------------------------------------------|
| `clips/`  | **You put raw footage here**                            |
| `footage/`| **Drop-zone for auto-stitching**: every clip in here gets combined into one edit |
| `music/`  | Music library (dubstep + chill house, see `MUSIC_CREDITS.md`) |
| `branding/` | Monitor Gear logos, fonts, colors (`brand.json` = source of truth) |
| `sponsors/` | Sponsor logos - included on request, 150px under the watermark |
| `output/` | Finished videos land here                               |
| `tools/`  | ffmpeg + the edit engine (`make_video.py`) - agent only |

## Auto-stitch (multiple clips -> one video)

Dump any number of clips into `footage/`, then:

    python tools\make_video.py stitch --duration 60 --format both --out output\my_edit

- Every video file in `footage/` is scanned (mp4/mov/m4v/avi/mkv/webm)
- The planner picks the **best window from any clip** for each role
  (action, scenic, calm, money shot) — no manual ordering needed
- Music: omit `--music` for an auto-pick from the brand-default pool,
  or name a track; `--seed N` makes the pick reproducible
- Prefix filenames `01_`, `02_` to bias ordering/ties
- Same Siruma structure, branding, beat-snapping and 4K support as everything else
- `--plan-only` writes the shot list JSON for hand-tuning

## Branding (automatic)

Every render pulls from `branding/brand.json` (extracted from monitorgear.me):
- **Watermark:** logo top-right, whole video
- **Intro card:** logo + `///UNLEASH YOUR SPIRIT`
- **Kinetic word pops:** `ADRENALINE`, `CHALLENGES`, `ADVENTURE`, `EXPLORATION`
  (or custom text/sub lines per edit)
- **Outro card:** logo + `UNLEASH YOUR INNER MAVERICK` + `FOLLOW @monitorgear` + monitorgear.me
- Fonts: Archivo Black (display) + Sora (support), colors: #ff0000 red, #d0e000 lime

Disable with `--nobrand`. Customize with an `overlays` array in the shots JSON:
`[{"kind": "word|intro|outro", "text": "...", "sub": "...", "start": s, "end": e}]`

## Music genres

- **Chill house / melodic electronic** (Uncan, Troigo, Stirquoise, John Bartmann)
  - default for edits; slower pacing, longer scenic holds
- **Dubstep** (DUBSTEP ATTACK series) - available on request for heavy edits
- All tracks pre-analyzed in `music/library.json` (BPM, beat grid, drop point)

## Siruma style (music-first editing)

Learned from the user's original edit (`clips/Siruma.mp4`, 108.5s @ 152 BPM) -
the signature moves are now built into the engine:

- **Dark logo intro card** -> **glitch/static bridge** on the first musical hit
- Scenes cut at **musical phrase boundaries**, snapped to the beat
  (the original had a cut 2ms off the beat)
- **B-roll bridge bursts**: rapid 0.3-0.4s texture close-ups (zoomed cutaways)
  exactly at musical hits, previewing the money shot
- The **quiet breakdown** gets its own calm scene, entered on a beat
- **Flash-to-black flicker** into the biggest energy section
- **Long immersive hold** on the money shot during the peak (contrast!)
- Minimal `WWW.MONITORAGEAR.ME` outro over footage -> fade to black

Auto-edit a clip into this structure:

    python tools/make_video.py auto --clip clips/IMG_3729.MP4 ^
      --music "VVVV" --duration 40 --format both --out output/my_video

Add `--plan-only` to just write the shot list JSON (then tweak by hand and
`build` it). The planner scouts footage automatically (motion + color scores)
and snaps every cut to the music's beat grid.

## Music library

All tracks in `music/` are cleared for **commercial use**:
- **DUBSTEP ATTACK 1-9 & 666** (Soundtrack 4 Life) - CC0, no attribution required
- Piano Dubstep Score (Joseph Sacco) - CC BY 4.0, attribution required
  (credit: "Joseph Sacco - Piano Dubstep Score, CC BY 4.0")

`music/library.json` holds each track's BPM, beat grid and drop point - that's
what makes beat-synced cutting possible. Re-run `python tools/analyze_music.py`
if you add tracks.

Ask the agent to fetch more tracks any time ("add some more heavy dubstep to
the music library").

## Engine internals (for the agent)

- `python tools/make_video.py analyze` - probe clips + extract preview frames
  to `tools/frames/<clip>/`; agent views frames, writes
  `tools/edits/<name>.shots.json` with chosen segments/speeds
- `python tools/make_video.py build --shots tools/edits/<name>.shots.json
  --music "track name" --format both|9:16|16:9 --out output/<name>`
- Shot JSON: `{"shots": [{"clip": "...", "start": s, "end": e, "speed": 1.0}]}`
  - `speed` 0.5 = slow-mo, 1.5 = sped up; display length = (end-start)/speed
- Color punch, 30 fps, CRF 20, faststart are baked in.
