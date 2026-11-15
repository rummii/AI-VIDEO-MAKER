Drop sponsor logos in this folder.

Rules
-----
- PNG with transparent background works best (JPG/WebP also accepted).
- Square-ish logos look best; every logo is rendered at a FIXED 150x150 px
  (same size as the watermark) in both 9:16 and 16:9 renders.
- Multiple logos stack vertically under the Monitor Gear watermark,
  top-right, right-aligned.
- File order = alphabetical (prefix filenames 01_, 02_ to control order).

Usage
-----
- Ask the agent to "include sponsor logos" when building, or add:
      --sponsors auto          (use every logo in this folder)
      --sponsors "a.png,b.png" (specific logos, specific order)
  to a build/auto command.

No logos in the folder = no sponsor overlays, nothing changes.
