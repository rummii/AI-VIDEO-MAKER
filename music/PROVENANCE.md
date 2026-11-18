# Music provenance log

Record every track used in a published video. This is your evidence if a
Content ID claim appears.

| Video | Track | Source | License | Claim status |
|---|---|---|---|---|
| `kite_sunset_120s` ("Birthday PAPA" on YouTube) | Deep House Sunset — sunset-house-grooves | https://pixabay.com/music/soft-house-deep-house-sunset-538759 | Pixabay Content License | **CLAIMED** by Elite Alliance Music — video blocked globally; dispute kit: `CLAIM_DISPUTE.md` |
| `last_bus_home_120s` | Last Bus Home — openmindaudio | https://pixabay.com/music/house-deep-house-last-bus-home-580584/ (verify exact URL) | Pixabay Content License | none reported yet |
| earlier batch (34 user uploads, 18 Nov 2026) | various Pixabay tracks | filenames contain Pixabay IDs — look up each `https://pixabay.com/music/...<id>` | Pixabay Content License | unknown — check before publishing |

## To add a row

Include: video name, exact track title + artist, direct Pixabay/track URL,
license type, and whether a claim appeared. Keep the License Certificate
(.txt from Pixabay) next to the MP3 in `music/provenance/` if available.
