# Instagram Vertical Teaser (9:16)

Converting a horizontal cinematic montage to Instagram Reels / Stories format.

## Specifications

- **Format**: 1080×1920 (9:16 portrait)
- **Frame rate**: 30 fps
- **Codec**: H.264 + AAC
- **Bitrate**: 8-12 Mbps (Instagram re-encodes anyway)
- **Movflags**: `+faststart` (streaming optimization)
- **Max duration**: 90s (Reels) · 15s (Stories) · 60s (sweet spot for engagement)

## Cropping strategies

The source is 3840×2160 (16:9). Target is 1080×1920 (9:16). Need to drop horizontal info or pad vertically.

### Option A — Center crop (default, fast)

```
crop=ih*9/16:ih,scale=1080:1920
```

- Crops 1215×2160 from horizontal center, scales to 1080×1920
- Works for **centered subjects** (drone shots typically are)
- Loses information left and right
- One ffmpeg call, fast

### Option B — Fit with letterbox (preserves all content)

```
scale=1080:-1,pad=1080:1920:0:(1920-ih)/2:color=black
```

- Source scales to 1080 wide, ~608 tall (16:9 scaled)
- Black bars top and bottom
- "Cinema in your phone" feel
- Loses immersion (lots of black)

### Option C — Smart crop per shot (best quality, slow)

Each plan gets its own crop window centered on the most important visual:

```python
PLAN_CROPS = {
    "#14 cascade":     (x=1280, y=0, w=1215, h=2160),   # cascade is left-of-center
    "#21 chateau":     (x=1500, y=0, w=1215, h=2160),   # castle is centered
    "#16 route_lac":   (x=1100, y=0, w=1215, h=2160),   # road descending right
}
```

Most effort but the best result for editorial work.

## Two deliverables per project

### Full vertical (entire film cropped)

```bash
ffmpeg -i master_4k.mp4 \
  -vf "crop=ih*9/16:ih,scale=1080:1920" \
  -c:v libx264 -preset fast -crf 20 \
  -c:a copy -movflags +faststart \
  output_vertical_full.mp4
```

- Same length as master (e.g. 3 min)
- For YouTube Shorts / IGTV / personal use
- Good as "long form vertical" archive

### Reels teaser (60s highlight)

Pick the most cinematic 60-second window of the master:

```bash
ffmpeg -ss 70 -t 60 -i master_4k.mp4 \
  -vf "crop=ih*9/16:ih,scale=1080:1920" \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 192k -movflags +faststart \
  output_reels_60s.mp4
```

For the Interlaken project: `-ss 70 -t 60` covers cascade → rotation → route → lake reveal (Act 2.5 to Act 3.5). Most visually dense minute.

## Selecting the 60-second window

Pick the segment that has:
- **Visual climax in the middle** (cascade, castle, lake reveal)
- **Quiet opening to hook** (not the most explosive shot first)
- **A satisfying closing shot** (lake reveal, drone descent)
- **Music in its energetic section** (not the calm intro/outro)

For most drone montages this is **the central minute** — typically t=70-130s of a 3-min film.

## Adding text overlays for Reels

Reels reward in-video text. Optionally add a hook in the first 1-2s:

```python
from PIL import Image, ImageDraw, ImageFont
# Generate "INTERLAKEN" overlay PNG (1080×1920 transparent)
# Then in ffmpeg:
# -i base.mp4 -i overlay.png -filter_complex "[0][1]overlay=enable='between(t,0,2)'" out.mp4
```

For Lou_Juicy style: don't add text. Let the cinematography speak. The user scrolling will pause regardless.

## Audio considerations

For Reels:
- Original audio works (music + SFX from master)
- Or strip audio and use a trending Instagram audio (max algorithmic reach)
- Always keep music below copyright threshold (royalty-free music = safe)

To strip audio:
```bash
ffmpeg -i reels.mp4 -c:v copy -an reels_silent.mp4
```

Then in Instagram app, pick a trending audio at upload.

## 1:1 square teaser (IG feed)

For a feed post (vs Reels), 1:1 square works:

```bash
ffmpeg -ss 80 -t 60 -i master_4k.mp4 \
  -vf "crop=ih:ih,scale=1080:1080" \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 192k -movflags +faststart \
  output_square_60s.mp4
```

Less impactful than 9:16 Reels, but useful for grid aesthetics.

## Pipeline diagram

```
master_4k.mp4  (3840×2160, 3min)
       ↓
   ┌───┴───┬───────┬─────────┐
   ↓       ↓       ↓         ↓
 YouTube   Reels   IG Feed   Stories
 4K          9:16    1:1       9:16 ≤15s
 (full)      (60s)   (60s)     (multiple)
```

All output from the same 4K master via ffmpeg filter chains. No re-rendering required — just transcode.
