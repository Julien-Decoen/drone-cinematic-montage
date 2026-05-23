---
name: drone-cinematic-montage
description: Build a cinematic montage from drone footage with ffmpeg — color grading per-clip, motion smoothing for slowmo, form-match cuts, music sync, SFX layering. Iterative preview-first workflow.
when_to_use: User has drone footage clips + an audio track and wants a polished cinematic edit (single video output).
---

# Drone Cinematic Montage — Skill

End-to-end workflow for building a cinematic montage from drone clips using ffmpeg + Python. The skill produces a single MP4 (preview 640×360 OR final 4K 3840×2160) with:

- per-clip color grading (LUT blend + curves + saturation + vignette)
- exposure recovery for underexposed clips (S-curve + warm shift, preserves deep blacks)
- motion-compensated frame interpolation for smooth slowmo on low-fps sources
- form-match cuts (perpendicular alignment between adjacent shots)
- music-synchronized act transitions
- per-clip + global SFX layering (wind ambient, riser, whoosh, etc.)

## When to invoke this skill

Trigger words: "drone montage", "cinematic edit", "drone cinematic", "drone reel", "video montage from clips".

Don't invoke for:
- Single-clip processing (just use ffmpeg directly)
- Music videos with full editing — this is drone-focused
- Heavy VFX work — this is grading + cuts only

## Required inputs from user

1. **Drone clips folder** — typically pre-segmented MP4 files (one shot per file or one shot per segment)
2. **Music track** — MP3 or WAV (becomes the timeline backbone)
3. **Optional**: a `.cube` LUT for the color base (Orange-Teal or similar)

## High-level workflow

Always **preview-first** — never render 4K before the preview is validated. Iterate on color, timing, cuts at 640×360 (renders in ~5 min). 4K render takes 30-90 min depending on minterpolate usage.

```
1. Probe clips (ffprobe)         → get durations + fps
2. Build EDIT list                → order, src_start, out_dur, speed, sfx, reframe
3. Configure CLIP_GRADE           → per-clip LUT/sat/gamma overrides
4. Set ACT_TRANSITIONS to music   → identify peaks in the audio
5. Render preview                 → QUALITY=preview python3 script.py
6. Generate storyboard            → 4×N grid of plan thumbnails
7. Iterate (color / cut / speed)  → loop steps 2-6
8. Render 4K final                → QUALITY=final python3 script.py
```

## Architecture — single Python script

Use the reference `examples/interlaken_v16.py` as starting point. Copy → modify EDIT + CLIP_GRADE + paths. The script has these phases:

```
main()
├── 1. Generate PNG overlays (title, outro, credits)
├── 2. process_clip × N        → render each plan to a sub-MP4 (TMP/clip_NN_J.mp4)
├── 3. render_xfade_pair       → handle xfade transitions
├── 4. process_outro           → render outro with overlay baked
├── 5. process_end_credits     → black + credits PNG
├── 6. Concat main video       → all sub-clips into main_video.mp4
├── 7. Apply title overlay     → fade-in PNG over clip #2
├── 8. Concat full             → main + outro + credits
└── 9. Final encode            → grain + audio mix (music + SFX + stings + outro)
```

Cache: each sub-clip is named by index → resumable. If you change `src_start` or `speed` of a plan, **delete its cached `clip_NN_*.mp4` files** before re-running.

## EDIT list structure

```python
EDIT = [
    # (fname, src_start, output_dur, speed, sfx, reframe, extra)
    ("DJI_...0102.MP4",  0.3, 4.0, 0.85,         "ambient", (1.0, 1.05), "hflip"),
    ("DJI_...0090.MP4",  4.0, 8.0, (0.5, 0.7),   "lapping", None,        None),
    # ...
]
```

- `src_start` (sec) — where in the source clip to start
- `output_dur` (sec) — duration in the OUTPUT timeline
- `speed` — float (`0.85` = slowmo) or tuple `(s_start, s_end)` for ease-in-out ramp
- `sfx` — SFX type name (see `make_sfx`)
- `reframe` — `(zoom_start, zoom_end)` for Ken Burns push (None = no zoom)
- `extra` — `"hflip"` to horizontally flip

The actual **source consumed** = `output_dur × speed`. Make sure `src_start + output_dur × speed ≤ source_duration`.

## CLIP_GRADE — per-clip color overrides

Inside `process_clip`, override the global `LUT_STRENGTH` / `SAT_MULT` baseline per clip:

```python
CLIP_GRADE = {
    "filename_substring": {
        "lut": 0.45,                # LUT blend strength (0=no LUT, 1=full)
        "sat": 0.85,                # saturation multiplier
        "gamma": 1.08,              # gamma lift (for dark clips)
        "exposure_fix": True,       # apply S-curve + warm shift (see exposure-recovery.md)
    },
    ...
}
```

Strategy:
- **Bright over-saturated plans** (greens/teals popping too much): lower `lut` (0.35-0.45) + lower `sat` (0.78-0.88)
- **Dark plans** (luma < 85): add `gamma`: 1.08-1.18
- **Cold cast plans** (overcast, blue-grey): set `exposure_fix: True` to apply curves + warm shift while preserving deep blacks
- **Match neighbors**: extract frames, measure `signalstats` `SATAVG`, align clips to within ±2 of each other

See `docs/color-grading.md` for the full diagnostic workflow.

## Motion smoothing — minterpolate

Slowmo from 30fps sources at speed < 0.9 produces effective <27fps output → judder ("saccadé"). The fix is **motion-compensated frame interpolation** applied BEFORE setpts:

```python
# In process_subseg, when src_fps < 50 and speed < 0.9:
interp_chain = "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
```

- `fps=60` is enough for 30fps × 0.5x (effective 30fps after interp + setpts)
- `fps=120` is overkill at 4K (3-4× slower render) and only marginal improvement
- `mci+aobmc` = motion compensated with adaptive overlapped block (best quality)

Don't apply on clips where speed ≥ 0.9 (no benefit, costs CPU).

See `docs/motion-smoothing.md`.

## Exposure recovery — S-curve + warm shift

For underexposed cloudy/overcast clips with cold cast (e.g. shot in evening light at mountain shadow), naive `eq=brightness` lifts blacks to grey. Instead use **shadow-compressed S-curve + colorbalance warm shift**:

```python
"[bl]curves=master='0/0 0.05/0.02 0.20/0.27 0.50/0.62 0.80/0.88 1/1':all='0/0 1/1',"
"colorbalance=bs=-0.05:bm=-0.03:bh=-0.02,"
"eq=saturation=1.10:gamma=1.08:contrast=1.080,"
```

- Curve compresses 0-0.05 toward black (deep blacks preserved)
- Lifts mids (0.20→0.27, 0.50→0.62)
- Pushes highlights (0.80→0.88)
- `colorbalance bs=-0.05` removes 5% blue from shadows = neutralizes cold cast

Verify with `signalstats`:
- `YMIN` should stay near 0 (deep blacks)
- `% pixels < 10` should match neighbors (~2-5%)
- `SATAVG` should be within ±2 of neighbors

See `docs/exposure-recovery.md`.

## Form-match cuts (perpendicular alignment)

Cinematic cuts where adjacent shots share visual line orientation. Used to bridge between visually-similar top-down drone shots:

1. Identify the dominant linear structure in each clip (rails, road, river, bridge)
2. Find frames where each line is at a **specific orientation** (vertical, diagonal, etc.)
3. Use `Hough line transform` or **visual inspection grids** to locate exact frames
4. Set `src_start` to land the cut frame on that orientation

For rotating drones (yaw):
- Measure the angular velocity (°/sec) of each clip
- Use ORB+RANSAC feature matching between consecutive frames → `cv2.estimateAffinePartial2D` → rotation angle
- Choose playback speeds so **`source_yaw_rate × playback_speed`** matches across both clips
- E.g. clip A natural 14°/s + clip B natural 24°/s → A at 1.25× and B at 0.74× both give 17.7°/s

See `docs/match-cuts.md` for the scripts.

## Music sync

The track's emotional peaks dictate the structure. Identify them once via RMS analysis or by ear, then align ACT cuts to those timestamps:

```python
ACT_TRANSITIONS = [18.0, 37.0, 74.0, 110.0, 129.0]  # music peaks (s)
```

When tweaking durations, recompute cumulative cut times and verify each Act boundary lands within **±1.5s** of a peak. If off by more, adjust nearby plan durations.

A `make_sting()` boom is mixed in at each ACT_TRANSITIONS time minus 0.8s (anticipation).

See `docs/music-sync.md`.

## SFX layering

Per-clip SFX (in `make_sfx`) — synthetic-only via `lavfi`:

- `ambient` — dual sine drone
- `lapping` — pink noise + low-pass + slow tremolo (water)
- `birds` — dual sine + tremolo/vibrato (chirps)
- `cascade_fade` — white wash + low rumble + droplets, with mid-clip fade
- `train` / `train_whistle` — low rumble + sine whistle
- `whoosh` — bandpass pink noise burst
- `boom` — 50Hz sine swell
- `riser` — frequency-rising bass + high-noise pad (for accelerating clips)
- `outro_ambient` — layered bass + footsteps + wind

Global layers (in final mux):
- `wind_global` — continuous subtle pink noise (volume ~0.65)
- `match_whoosh` — single whoosh at form-cut points (volume ~0.55)
- act stings (boom) at each `ACT_TRANSITIONS` minus 0.8s

Balance reference (in final mix):
- music = 0.85
- per-clip SFX summed = 0.28
- outro SFX = 0.55 (delayed to outro start)
- stings = 0.55
- wind global = 0.65 (its volume is internal in make_sfx, this is the mix gain)
- match whoosh = 0.55

See `docs/sfx-layers.md`.

## Iteration loop

The user will iterate many times. Follow this loop strictly:

1. Apply ONE category of changes (e.g. color, or timing, or SFX — not all at once)
2. `rm -rf <TMP_dir>` if structural changes (EDIT order, new clips, resolution)
3. `QUALITY=preview python3 script.py` (5-8 min)
4. Generate a storyboard grid (24 thumbnails, label changed plans in orange)
5. Show storyboard + ask specific validation questions
6. Iterate

Don't make 5+ changes at once — user can't isolate what worked.

## Performance — 4K render

- 4K (3840×2160) with minterpolate fps=60: ~30-45 min for ~22 plans
- 4K without minterpolate: ~15-20 min
- On macOS M1 MBP unplugged: drain ~40% battery for full render
- Use `caffeinate -i -s -w <PID>` to prevent sleep during render
- If render is interrupted, the sub-clip cache resumes from last `clip_NN_J.mp4`

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Scintillement (flicker) | `noise=allf=t+u` (temporal flag) | Use `allf=u` only |
| Saccadé (judder) on slowmo | 30fps source × 0.5x = 15fps effective | Add `minterpolate=fps=60` before setpts |
| Grey/muddy blacks | `eq=brightness=+0.X` lifts black point | Use `curves` with anchor at 0/0 instead |
| Color mismatch between clips | Single LUT applied uniformly | Per-clip `CLIP_GRADE` overrides |
| Cuts feel "off" to music | Drift from added/removed seconds | Recompute cumulative times, target peaks ±1.5s |
| Whites becoming grey on overlay | `eq=brightness` on outro | Use gamma + contrast (preserves whites) |
| PNG title appears smaller after 4K | Hardcoded pixel sizes | Use `S(x) = int(x * SCALE)` where SCALE = OUT_W/3840 |

## Reference files

- **[PROCESS.md](PROCESS.md)** — Full A-to-Z workflow with music recommendations (READ THIS FIRST)
- **[docs/delivery-checklist.md](docs/delivery-checklist.md)** — Turn-key 10-phase checklist for every new project
- `examples/interlaken_v19.py` — Reference impl (cars SFX + audio mix balance)
- `examples/interlaken_v16.py` — Earlier reference (exposure_fix introduced)
- `templates/edit_template.py` — Bare-bones starter
- `docs/` — Detailed guides per topic (see below)
- `scripts/analyze_rotation.py` — Measure yaw rotation rate for match cuts
- `scripts/analyze_sat.py` — Per-clip signalstats analysis
- `scripts/find_perpendicular.py` — Find perpendicular line frames

## Detailed guides

| Topic | Doc |
|---|---|
| Music selection + sync | `docs/music-sync.md` |
| Color grading + per-clip overrides | `docs/color-grading.md` |
| Exposure recovery (S-curve + warm shift) | `docs/exposure-recovery.md` |
| Motion smoothing (minterpolate) | `docs/motion-smoothing.md` |
| Form match cuts (perpendicular + rotation) | `docs/match-cuts.md` |
| **SFX layers (synthetic recipes + balance)** | `docs/sfx-layers.md` |
| **SFX real via ElevenLabs API** | `docs/sfx-real-elevenlabs.md` |
| **Audio mixing methodology (iterative)** | `docs/audio-mixing.md` |
| **YouTube delivery (thumbnail/banner/title/description)** | `docs/youtube-delivery.md` |
| **Instagram vertical 9:16 teaser** | `docs/instagram-vertical.md` |
| **Turn-key delivery checklist** | `docs/delivery-checklist.md` |
| Iteration loop details | `docs/workflow.md` |

## When the user asks "comment je commence"

Point them to **PROCESS.md** + **delivery-checklist.md**. The first describes the methodology; the second is a concrete to-do list to publish a new film.

The skill's value is the **process**, not just the script.
