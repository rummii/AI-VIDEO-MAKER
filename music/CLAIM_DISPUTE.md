# Content ID claim — dispute kit

## What happened

A video using **Deep House Sunset** by sunset-house-grooves got a YouTube
Content ID claim from **Elite Alliance Music**: video blocked globally, not
eligible to earn. This is a **claim**, not a copyright strike — your channel
standing is unaffected.

**Why it happened even though the track is legal:** Pixabay's Content License
allows commercial use, but some artists/distributors ALSO register their
tracks in YouTube's Content ID system. The matcher doesn't read your license;
it just detects the audio fingerprint and applies the claimant's rules.

## Immediate fix (recommended): dispute with license proof

1. Log into Pixabay, open the track page:
   https://pixabay.com/music/soft-house-deep-house-sunset-538759
2. Under the **Download** dropdown (or the download pop-up), download the
   **License Certificate (.txt)** — it's available to logged-in users.
3. In YouTube Studio → **Content** → find the video → **Restrictions →
   Claims → See details → Take action → Dispute**.
4. Choose: **"I have permission or a license to use the content."**
5. Paste this rationale (edit video ID/date if needed):

> I licensed this audio from Pixabay under the Pixabay Content License.
> Track: "Deep House Sunset" by sunset-house-grooves.
> Source URL: https://pixabay.com/music/soft-house-deep-house-sunset-538759
> License: https://pixabay.com/service/license-summary/
> The track is used as background music in my video "Birthday PAPA".
> I have attached/downloaded the Pixabay License Certificate for this track
> and can provide it on request.

6. Attach the license certificate if the form allows it. Submit.
   The claimant has **30 days** to respond; if they don't, the claim is
   released automatically.

## Alternative paths

- **Contact the author** via https://pixabay.com/users/sunset-house-grooves-54751244
  with a link to the video — they can often release the claim faster.
- **YouTube's "Replace song" / "Mute song"** in the claim panel — instant
  unblock, but you lose the soundtrack (re-upload with a different track).
- **Trim claimed segment** — only works if the claimant allows a short
  excerpt; your message says they don't (exceeds length limits).

## If the dispute is rejected

A second-level appeal is possible, but if the rights holder rejects again it
can escalate toward a strike. Only escalate with the license certificate in
hand. When in doubt, replace the music instead.

## Prevention for this pipeline

Before using any Pixabay track in a public video:
- Check the track page for a **Content ID** flag.
- Download the **License Certificate** at download time and store it in
  `music/provenance/` (track name, URL, date, certificate).
- Prefer **YouTube Audio Library** (no Content ID claims by design) or
  **Mixkit** (Envato's Claim Clear process) for videos that must stay
  monetizable without disputes.

See `music/PROVENANCE.md` for the log of tracks used in this project.
