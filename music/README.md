# Music library

All audio files in this folder are from **Pixabay** under the Pixabay Content
License: free commercial use, no attribution required. Just don't resell the
raw file standalone, or use embedded brands/trademarks commercially.

34 tracks were added on 18 Nov 2026 (deep house, vocal house, trance,
psytrance, synthwave, chill, hardstyle, phonk, cloud rap) plus the earlier
"The Realest Thought" by openmindaudio.

`library.json` holds the analyzed BPM/beat-grid/drop point for every file here.
Use a filename (or distinctive part of it) with `--music` in the build/auto/
stitch commands, e.g.:

    python tools\make_video.py build --shots <plan>.shots.json --music "khemrajdotin-deep-house" --format both --out output\<name>

See `GENRE_BRIEF.md` for the Chill Pop / Downtempo search brief and
`MUSIC_CREDITS.md` for the full license record (including sources removed
earlier: Mixkit, incompetech, FMA, FreeToUse).
