# Delivery Checklist — Turn-Key Project Process

Everything to ship a cinematic drone montage from raw footage to published YouTube/Instagram. Use this checklist for every new project.

## Phase 0 — Pre-flight (before any code)

- [ ] All drone clips downloaded to `<project>/export/` folder
- [ ] Music track downloaded (royalty-free, with credit URL)
- [ ] LUT file `.cube` chosen
- [ ] Target project name (e.g. `Interlaken26`)
- [ ] Companions' names (for credits)
- [ ] Approximate locations list (for descriptions)
- [ ] Free 10 GB on `/tmp` for cache (4K renders take space)
- [ ] Mac plugged in (4K render = ~40 min, drains battery)

## Phase 1 — Script setup

- [ ] Copy `templates/edit_template.py` to `/tmp/<project>_v1.py`
- [ ] Update path constants (CLIPS, MUSIC, OUTPUT, FONT)
- [ ] Probe clip durations + fps (`ffprobe`)
- [ ] Probe music duration + identify RMS peaks → `ACT_TRANSITIONS`

## Phase 2 — First EDIT pass (v1-v3)

- [ ] Draft EDIT list (5-7 plans per Act, 4-5 Acts)
- [ ] Default SFX assignments (best guess per visual)
- [ ] Title PNG generation (right-aligned Didot)
- [ ] Outro PNG generation
- [ ] Credits PNG generation
- [ ] Render preview (`QUALITY=preview`, ~5-8 min)
- [ ] Storyboard grid 4×N → review with user
- [ ] Iterate timing/order until user approves structure

## Phase 3 — Color grading (v4-v6)

- [ ] Probe luma + chrominance per plan (`signalstats`)
- [ ] Identify outliers (greens too vivid, dark plans, cold cast)
- [ ] Add `CLIP_GRADE` overrides for each
- [ ] Apply `exposure_fix: True` on underexposed cold-cast plans (S-curve + warm shift)
- [ ] Tune vignette angle (PI/4 for cinema visible at 4K)
- [ ] Preview render → validate

## Phase 4 — Motion + cuts (v7-v9)

- [ ] Slowmo plans (speed < 0.9 on 30fps sources): add `minterpolate=fps=60`
- [ ] Remove speed ramps user finds saccadé (use lowest or highest constant)
- [ ] Identify match cut opportunities (perpendicular lines, rotation matching)
- [ ] Add `hflip` on plans where mirror improves composition
- [ ] Preview render → validate motion smoothness

## Phase 5 — Music sync (v10-v12)

- [ ] Compute cumulative cut times
- [ ] Adjust plan durations so Act boundaries land within ±0.5s of music peaks
- [ ] Round durations to integer frame counts (multiples of 1/FPS) for frame-perfect sync
- [ ] Preview render → user listens for sync

## Phase 6 — SFX (v13-v17)

- [ ] Choose: synthetic (lavfi) or real (ElevenLabs)
- [ ] If ElevenLabs: register, store API key in `/tmp/.el_key`, batch-generate ~15 SFX with scene-specific prompts (see [sfx-real-elevenlabs.md](sfx-real-elevenlabs.md))
- [ ] Measure each SFX loudness (`volumedetect`)
- [ ] Categorize per-plan: ambient / info / climax / fx
- [ ] Build first mix (Mix A) with category-based targets
- [ ] Build storyboard-with-sound video (1 frame/plan + audio)
- [ ] User feedback → mix B, C, D, ...
- [ ] Lock the final mix (typically takes 5-15 iterations)

## Phase 7 — Title/outro overlays (v18-v19)

- [ ] Title PNG: Didot main + Helvetica sub, no drop shadow
- [ ] Title position (y=0.65 or 0.75) — let user pick
- [ ] Fade-only animation (no horizontal slide)
- [ ] Outro PNG: same style, English text recommended
- [ ] Credits PNG: include all credits (location, drone, edit tool, music URL, IG)
- [ ] If using Claude AI: add "Edited with Claude (Anthropic)" to credits

## Phase 8 — 4K master render

- [ ] `caffeinate -i -s -d -u -w <PID>` to prevent sleep
- [ ] Mac on AC power (M1 unplugged drains 25-40%)
- [ ] `QUALITY=final python3 script.py` (~35-45 min)
- [ ] If cache reuse possible (from previous version), only impacted plans re-render
- [ ] Verify final: `ffprobe` shows 3840×2160 · 178s ± 0.1s · h264+AAC · ~40 Mbps

## Phase 9 — Delivery assets

### YouTube (see [youtube-delivery.md](youtube-delivery.md))

- [ ] **Thumbnail** 1920×1080 JPG · 4 candidates → user picks
- [ ] **Title** — location-first, ≤60 chars, cinematic
- [ ] **Description** — hook + locations + gear + music credit + chapters + IG
- [ ] **Channel banner** 2560×1440 JPG · tagline only, letterbox style
- [ ] **Channel description** — tagline + 2-3 sentences + gear + IG
- [ ] **Tags** — 10-15 specific (location, gear, style)

### Instagram (see [instagram-vertical.md](instagram-vertical.md))

- [ ] **9:16 full vertical** (entire film, center crop, ~178s)
- [ ] **9:16 Reels 60s** (most cinematic minute, t=70-130s typically)
- [ ] **1:1 square 60s teaser** (optional, for feed grid)

### Archive

- [ ] Copy all `v*.py` scripts → `<project>/_resources/scripts/`
- [ ] Copy SFX library → `<project>/_resources/sfx/`
- [ ] Copy storyboard PNGs → `<project>/_resources/storyboards/`
- [ ] Copy thumbnail/banner candidates → `<project>/_resources/youtube/`
- [ ] Copy final mix MP3 → `<project>/_resources/audio/`

## Phase 10 — Publication

- [ ] Schedule YouTube upload for evening (best engagement)
- [ ] Visibility: Public, comments ON
- [ ] Set end screen (next video + subscribe)
- [ ] Add captions (auto-gen then review for accuracy)
- [ ] Tease on Instagram 6-24h before YT release (Stories + Reels)
- [ ] Cross-link IG ↔ YouTube
- [ ] Set up notification for new subscribers / comments

## Typical timeline

For a similar project (~22 plans, 3 min):

| Phase | Duration |
|---|---|
| Discovery + EDIT pass | 1-2 hours |
| Color grading iterations | 30-60 min |
| Motion + cuts | 30-60 min |
| Music sync | 15-30 min |
| SFX (with ElevenLabs) | 1-2 hours (mostly iterating mix) |
| Title/outro design | 30 min |
| 4K render | 35-45 min (often background) |
| YouTube assets | 30-60 min |
| **Total** | **5-8 hours** spread over 1-2 sessions |

For repeat projects (similar location/style): can drop to 3-4 hours since color/sync templates already proven.

## Iteration tips

- **One change category per iteration** (color, OR timing, OR SFX — not all)
- **Always preview first** at 640×360 before 4K
- **Cache aggressively** (sub-clip rendering is the expensive step)
- **Frame-perfect sync only matters once timing is close** — first pass approximate, refine
- **Present 2-3 options per round** rather than one — user picks faster
- **Audio iterations don't need video re-render** — use storyboard slideshow video
