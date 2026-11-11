# PROCESS — End-to-end workflow

> The complete A-to-Z process for building a cinematic drone montage, distilled from **21 iterations** on the Interlaken project, including ElevenLabs SFX integration, audio mixing methodology, YouTube delivery and Instagram vertical export.

**For a turn-key checklist** (do this on every project): see [docs/delivery-checklist.md](docs/delivery-checklist.md).

---

## Phase 0 — Discovery & assets

### 0.1 What you need

| Asset | Required | Notes |
|---|---|---|
| Drone clips folder | ✅ | Pre-segmented MP4s, ideally one shot per file or per segment |
| Music track | ✅ | Becomes the structural backbone |
| LUT file (.cube) | optional | Orange-Teal or similar for the base color grade |
| Title / location / dates | optional | For overlays |

### 0.2 Probe clips

```bash
for f in /path/to/clips/*.MP4; do
  ffprobe -v error -show_entries format=duration -show_entries stream=r_frame_rate -of csv=p=0 "$f"
done
```

You need to know:
- **Duration** of each clip (to budget for the EDIT list)
- **Frame rate** (30fps vs 60fps changes slowmo strategy → see [motion-smoothing.md](docs/motion-smoothing.md))

### 0.3 Identify hero shots

Quickly scrub each clip and tag:
- 🌟 **Hero** — must appear (best framing, most cinematic moment)
- 🟡 **Filler** — good but optional
- 🔴 **Skip** — bad framing, motion blur, or boring

Most projects have 15-25 hero + filler shots ending up in the final cut.

---

## Phase 1 — Music selection

The music dictates the **structure, tempo and mood**. Pick it FIRST, then build the video to match.

### 1.1 Style → recommended music

| Drone style | Music mood | Track examples |
|---|---|---|
| **Mountain / vast landscape** | Cinematic Ambient | Ludovico Einaudi · "Nuvole Bianche"  ·  Olafur Arnalds · "Near Light"  ·  Max Richter · "On the Nature of Daylight" |
| **City / aerial reveal** | Cinematic Epic | Hans Zimmer-style instrumental  ·  Two Steps From Hell · "Heart of Courage"  ·  Audiomachine |
| **Travel / lifestyle** | Chill electronic / Indie folk | Tycho · "Awake"  ·  Bonobo · "Cirrus"  ·  Bon Iver · "Holocene" |
| **Sunset / golden hour** | Warm ambient | Nils Frahm · "Says"  ·  Max Cooper · "Repetition" |
| **Action / fast cuts / sports** | Dynamic electronic | ODESZA  ·  Flume  ·  FKJ live edits |
| **Mystic / forest / fog** | Dark ambient | Olafur Arnalds + Nils Frahm · "Trance Frendz"  ·  Aphex Twin · "Avril 14th" |
| **Coastal / sea** | Reverby ambient | Tycho · "Plains"  ·  Helios · "Halving the Compass" |

### 1.2 Where to find music

| Source | Cost | Use |
|---|---|---|
| **Epidemic Sound** | paid subscription | Pro YouTube/social — best quality and search |
| **Artlist** | paid subscription | Cinematic library |
| **Musicbed** | paid subscription | High-end cinematic |
| **Pixabay Music** | free | Hobby projects |
| **YouTube Audio Library** | free | Quick prototypes |
| **Bensound** | free w/ attribution | Simpler tracks |
| **Uppbeat** | freemium | Recent indie tracks |
| **Nastelbom** (used here) | royalty-free (Pixabay) | "Cinematic Ambient" — perfect for mountain drone work |

### 1.3 Track requirements

For a cinematic drone montage, the ideal track has:
- **Duration** 2-4 min (≈ your target video length)
- **Clear emotional peaks** every 30-45s (these become your Act transitions)
- **Calm intro and outro** (5-10s) — lets your video breathe at start/end
- **Dynamic range** (quiet vs loud passages) → varied visual energy

### 1.4 Identify music peaks

```bash
ffmpeg -i music.mp3 \
  -af "astats=metadata=1:reset=0.05,ametadata=print:key=lavfi.astats.Overall.RMS_level" \
  -f null - 2>&1 | grep -E "pts_time|RMS_level"
```

Parse the output and find local RMS maxima. Validate by ear — the "felt" peak may be slightly earlier than the RMS max.

Set `ACT_TRANSITIONS = [...]` to those times in your script. See [music-sync.md](docs/music-sync.md).

---

## Phase 2 — Initial EDIT list

### 2.1 Act structure

A standard 3-minute cinematic montage has **5 acts** corresponding to music sections:

| Act | Theme example (Interlaken) | Music character | Duration |
|---|---|---|---|
| 0 — Awakening | Lake fog at dawn | Calm intro | 0:00–0:18 (18s) |
| 1 — Discovery | Villages, paths | Building | 0:18–0:37 (19s) |
| 2 — Movement | Train, urban motion | Energetic | 0:37–1:14 (37s) |
| 3 — Climax | Cascade, rotations | Peak emotion | 1:14–1:50 (36s) |
| 4 — Resolution | Lake at calm | Reflective | 1:50–2:09 (19s) |
| 5 — Finale | Châteaux, sunset | Crescendo | 2:09–2:40 (31s) |

Each act gets **5-7 plans**. Total: 25-35 plans for a 3min montage.

### 2.2 Define EDIT entries

```python
EDIT = [
    # (fname, src_start, output_dur, speed, sfx, reframe, extra)
    ("HERO_001.MP4",  0.3,  4.0, 0.85,         "ambient", (1.0, 1.05), None),
    ("HERO_002.MP4",  4.0,  8.0, (0.5, 0.7),   "lapping", None,        None),
    ...
]
```

- **src_start**: where in source clip to begin
- **output_dur**: duration in the OUTPUT timeline (this is what counts for music sync)
- **speed**: float (0.7 = slowmo) OR tuple `(s_start, s_end)` for ease-in-out ramp
- **sfx**: see [sfx-layers.md](docs/sfx-layers.md)
- **reframe**: `(zoom_start, zoom_end)` Ken Burns push or None
- **extra**: `"hflip"` to mirror horizontally

### 2.3 Music sync first pass

Compute cumulative cut times (sum of `output_dur` up to each plan, minus xfade overlaps):

```python
cum = 0
for i, e in enumerate(EDIT):
    cum += e[2]   # output_dur
    if i == act_boundary_idx:
        print(f"Act cut at {cum:.2f}s — target {ACT_TRANSITIONS[k]:.2f}s")
```

Adjust `output_dur` so each Act boundary lands within **±1.5s of the music peak**. Frame-perfect alignment (multiples of 1/FPS seconds) is the goal once timing is locked.

---

## Phase 3 — Color grading

### 3.1 Baseline grade chain

```
scale → LUT blend (50%) → eq (contrast, saturation, gamma) → vignette
```

Global defaults:
```python
LUT_STRENGTH = 0.50
SAT_MULT     = 0.90
CONTRAST     = 1.05
```

### 3.2 Per-clip overrides — CLIP_GRADE

For each clip that deviates from neighbors, add an entry:

```python
CLIP_GRADE = {
    "filename_substring": {
        "lut":   0.45,
        "sat":   1.10,
        "gamma": 1.08,
        "exposure_fix": True,
    },
    ...
}
```

Strategy (see [color-grading.md](docs/color-grading.md) for full details):

- **Bright over-saturated plans** (vivid greens/teals): lower `lut` (0.35-0.45) + lower `sat` (0.78-0.88)
- **Dark plans** (luma < 85): add `gamma`: 1.08-1.18
- **Cold-cast / overcast plans**: set `exposure_fix: True` (applies S-curve + warm shift while preserving deep blacks — see [exposure-recovery.md](docs/exposure-recovery.md))

### 3.3 Validate with signalstats

```python
import subprocess, re
def stats(t):
    r = subprocess.run([
        "ffmpeg","-ss",str(t),"-t","1","-i","preview.mp4",
        "-vf","scale=320:-1,signalstats,metadata=print",
        "-f","null","-"
    ], capture_output=True, text=True)
    y = [float(m) for m in re.findall(r"YAVG=([\d.]+)", r.stderr)]
    s = [float(m) for m in re.findall(r"SATAVG=([\d.]+)", r.stderr)]
    return y[len(y)//2], s[len(s)//2]
```

Compare neighbors. Target ±2 SAT delta between adjacent plans.

### 3.4 Vignette

Subtle radial darkening at edges to draw the eye to center. **In ffmpeg, larger angle = stronger vignette**:

- `vignette=PI/5` — default (subtle)
- `vignette=PI/4` — visible cinema
- `vignette=PI/3` — strong cinema (recommended for 4K output)
- `vignette=PI/2` — maximum (corners almost black)

---

## Phase 4 — Motion handling

### 4.1 Speed ramps cause "stepping"

Ramps split into `n_sub` sub-segments (default 5) with discrete speeds. The viewer perceives "steps" — looks like saccadé.

**Fix**: For problematic ramp plans, either:
1. Replace with **constant speed** (typically the lowest of the ramp = max slowmo)
2. Increase `n_sub` to 10-15 for smoother gradient

### 4.2 Slowmo on low-fps sources

30fps source × 0.5x speed = effective 15fps → visible judder.

**Fix**: motion-compensated frame interpolation BEFORE setpts:

```
minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,
setpts=2.0*PTS,
...
```

Apply when `src_fps < 50 AND speed < 0.9`. See [motion-smoothing.md](docs/motion-smoothing.md).

### 4.3 Match cuts

For shots that share visual line orientation (rails, road, river, bridge), pick frames where lines align:

1. Sample frames every 0.2-0.3s in candidate windows of both clips
2. Use Hough Transform or visual inspection to find perpendicular/diagonal alignment
3. Set `src_start` so the cut lands on aligned frames

For rotating drones (yaw), match the angular velocity by adjusting playback speeds:

```
target_rate = (source_yaw_A + source_yaw_B) / 2
speed_A = target_rate / source_yaw_A
speed_B = target_rate / source_yaw_B
```

See [match-cuts.md](docs/match-cuts.md).

---

## Phase 5 — Sound design (SFX layers)

For pro-quality results: use **real ElevenLabs SFX** (see [docs/sfx-real-elevenlabs.md](docs/sfx-real-elevenlabs.md)). Costs ~$0.10 / project, dramatically more cinematic than synthetic.

Workflow:
1. Identify which plans need which SFX (category mapping)
2. Generate real SFX via ElevenLabs API (15 prompts × ~10s = ~$0.10)
3. Measure loudness of each
4. Build initial mix with category-based gains
5. **Iterate audio mix** — propose 2-3 variants per round (see [docs/audio-mixing.md](docs/audio-mixing.md))
6. Validate with storyboard-with-sound video (1 frame/plan + audio), not full 4K re-render


### 5.1 SFX selection by visual context

For each plan, pick an SFX matching the **scene type** AND **camera distance**:

| Visual context | SFX |
|---|---|
| Calm landscape (lake, mountains) | `ambient` (dual sine drone) |
| Lake / water surface | `lapping` (water lapping) |
| Forest, fields, birds | `birds` (chirps) |
| Train station, urban | `train` or `train_whistle` |
| Cars (high altitude) | `cars_far` (distant rumble) |
| Cars (medium altitude) | `cars_mid` (audible engines) |
| Cars (low altitude) | `cars_close` (defined road noise) |
| Sailboat, marina | `sail` (filtered pink noise) |
| Camera reveal motion | `whoosh` (bandpass noise burst) |
| Cascade / waterfall | `cascade_fade` (water wash + rumble) |
| Castle / dramatic reveal | `boom` (sub bass sting) |
| Accelerating finale | `riser` (cubic-curve crescendo) |
| Outro / contemplative | `outro_ambient` (bass + footsteps) |

### 5.2 Audio mixing — the balance problem

Without normalization, your SFX recipes will have wildly different output levels. Cascade dominates, ambient is inaudible.

**Target volumes per recipe** (max amplitude after `volume=` and any amix):

| Recipe | Target | Notes |
|---|---|---|
| `cascade_fade` | 0.85-1.0 | Climax can be slightly louder |
| `whoosh` | 0.7-0.8 | Quick burst, present without spiking |
| `boom` | 1.0-1.5 | Single impulse, can be punchy |
| `ambient` | 0.5-0.6 | Background presence |
| `cars_far/mid` | 0.5-0.6 | Layered traffic, not dominant |
| `birds`, `train`, `lapping`, `sail` | 0.5-0.7 | Normalized |
| `riser`, `outro_ambient` | 0.7-1.0 | Climactic / closing |
| `wind_global` | 0.30 | Subtle continuous |

### 5.3 Final mix volumes

In the final encode `afilter`, balance the layers:

```
[music]   volume=0.85
[main_sfx] volume=0.50      // concatenated per-clip SFX
[outro_sfx] volume=0.55     // delayed to outro start
[stings]   volume=0.55      // act-transition booms
[wind_global] volume=0.65   // continuous background
[match_whoosh] volume=0.55  // form-cut single hits
```

These multiplicative values combine with the per-recipe internal volumes from §5.2. See [sfx-layers.md](docs/sfx-layers.md) for full balance reference.

### 5.4 Three layers of SFX

```
GLOBAL          wind_global (continuous, low volume) + match_whoosh (form cuts)
PER-CLIP        one SFX per EDIT entry, duration matches plan
TRANSITION      sting boom on each ACT_TRANSITIONS time (anticipation -0.8s)
```

---

## Phase 6 — Iteration loop

### 6.1 Preview-first rule

NEVER render 4K before preview is validated.

```bash
QUALITY=preview python3 script.py    # 640x360, ~5-8 min
```

Generate a storyboard grid (4-cols × N rows) with each plan labeled. Show to the user.

### 6.2 One category of changes at a time

Don't mix categories. The user can't isolate what worked if 5 things changed.

Categories (apply one per iteration):
- **A** — Order / structure (reorder, add/remove)
- **B** — Per-clip timing (`src_start`, `out_dur`, `speed`)
- **C** — Color grading (CLIP_GRADE)
- **D** — Motion smoothing (minterpolate flags)
- **E** — Match cuts (perpendicular alignment)
- **F** — Music sync (Act boundaries)
- **G** — SFX (selection + balance)
- **H** — Title / outro overlays

### 6.3 Cache invalidation

When you change EDIT structurally:
- Inserting/removing a plan → shift indices → delete impacted cache files
- Changing `src_start` or `speed` of plan #N → `rm /tmp/<project>/clip_NN_*.mp4`
- Changing `CLIP_GRADE` for plan #N → `rm /tmp/<project>/clip_NN_*.mp4`
- Resolution change (preview ↔ final) → `rm -rf /tmp/<project>/`

### 6.4 Validation questions

After each iteration, ask the user **specific** questions:
- ✅ Vignette visible aux coins ?
- ✅ Cut #N→#N+1 fluide ?
- ✅ SFX `cars_mid` sur #16 — bon volume ?
- ✅ Sync musicale toujours OK à 1:14 et 1:50 ?

Avoid vague questions like "ça te plaît ?".

---

## Phase 7 — Title and outro

### 7.1 Title overlay

Generate 2 PNGs:
- `TITLE_MAIN_PNG` — large headline (DIDOT 156px @ 4K)
- `TITLE_SUB_PNG` — subtitle (Helvetica Light 48px @ 4K)

Position:
- Right-aligned at `right_edge = OUT_W * 0.92`
- `main_y = OUT_H * 0.65 - main_h // 2` (slightly below center, classic third)
- Subtitle below main with `S(15)` gap

Animation:
- Both fade alpha in/out (no slide — feels cleaner)
- MAIN fades in at +1.0s into the title-bearing clip
- SUB fades in at +2.2s (1.2s after MAIN — staggered)
- Both fade out 0.7s before clip ends

### 7.2 Outro

Same structure as title but on the closing clip. Position lower-right (`OUT_H * 0.78`) so it overlays the parking surface / quiet area of the frame.

Text typically `THANK YOU / See you soon` or equivalent.

### 7.3 Fade-in from black

```
[v0]fade=t=in:st=0:d=1.2:color=black[v0]
```

Applied during the title-overlay pass on the first 1.2s of the main video.

---

## Phase 8 — Final 4K render

### 8.1 Pre-flight checks

- [ ] All preview iterations validated
- [ ] All `CLIP_GRADE` overrides set
- [ ] Music sync verified frame-perfect
- [ ] SFX balance validated by ear at preview
- [ ] Title / outro PNGs look correct in preview
- [ ] Mac on AC power (M1 unplugged can run out mid-render)

### 8.2 Launch

```bash
rm -rf /tmp/<project>/      # fresh cache (preview clips at 640x360 not reusable at 4K)
caffeinate -i -s -d -u python3 -u script.py   # with QUALITY=final
# or in background:
QUALITY=final python3 -u script.py > render.log 2>&1 &
RENDER_PID=$!
nohup caffeinate -i -s -d -u -w "$RENDER_PID" &
```

`caffeinate -i -s -d -u` prevents idle, system, display, and auto-lock sleep — render survives even if you close the lid (on AC).

### 8.3 ETA

For ~22 plans with `minterpolate fps=60` on ~16 of them:
- M1 MacBook Pro at 4K: **35-45 min**

Battery drain on M1 MBP unplugged: ~25-40% per render. **Use AC**.

### 8.4 Verification

```bash
ffprobe -v error -show_entries format=duration,size,bit_rate \
                  -show_entries stream=width,height,r_frame_rate \
                  -of default=noprint_wrappers=1 \
                  /Users/.../output.mp4
```

Expected: 3840×2160 · 30/1 fps · h264 · 40-50 Mbps · ~1 GB · target duration ±0.1s.

---

## Phase 9 — Delivery (YouTube + Instagram)

After 4K master is locked, produce the publishing kit:

### 9.1 YouTube package

See [docs/youtube-delivery.md](docs/youtube-delivery.md) for full details.

- **Thumbnail** 1920×1080 JPG — 4 candidates → user picks. Didot italic title + Helvetica subtitle on bottom-darkened hero frame.
- **Title** — Location-first, ≤60 chars, English: `[LOCATION] — [Storytelling] | [Quality]`
- **Description** — Hook + locations + gear + music credit (with URL) + chapters + IG link + tags
- **Channel banner** 2560×1440 JPG — letterbox cinema, **tagline only** (no channel name — YouTube displays it), text in 1235×338 safe area
- **Channel description** — Tagline first, then 2-3 sentences + gear + social
- **Tags** — 10-15 specific (location + gear + style)

### 9.2 Instagram vertical teasers

See [docs/instagram-vertical.md](docs/instagram-vertical.md).

- **Full vertical** (entire film 9:16 cropped, same duration as master)
- **Reels 60s** (most cinematic minute, typically t=70-130s)
- **Square 1:1 60s** (optional, IG feed grid)

All generated via ffmpeg from the same 4K master — no re-render required.

### 9.3 Archive

Copy to `<project>/_resources/`:
- All `v*.py` scripts (full version history)
- SFX library used
- Storyboard PNGs
- Thumbnail / banner candidates
- Final mix MP3

---

## Iteration timeline (Interlaken case study)

| Version | Focus | Iterations | Result |
|---|---|---|---|
| V1-V4 | Initial structure, music sync first pass | 4 | Rough cut |
| V5-V8 | LUT, color grading, per-clip overrides | 4 | Look locked |
| V9-V11 | Saccadé fixes (minterpolate), flicker fix (noise temporal) | 3 | Smooth motion |
| V12 | Per-clip sat/lut overrides on 16 plans | 1 | Color cohesion |
| V13 | exposure_fix S-curve on #2 + #14 (cold cast plans) | 1 | Deep blacks recovered |
| V14 | Match cut #10 → #11 NEW (vertical rails/bridge) | 1 | Form cut works |
| V15 | Music sync frame-perfect (±1.5s → ±0s) | 1 | Audio-visual lock |
| V16 | Yaw rotation matching, sat bumps, SFX additions | 1 | Smooth panning across cuts |
| V17 | Vignette + bug fixes (riser NaN) | 1 | Clean output |
| V18 | Speed ramps → constant (anti-saccadé) | 3 | All saccadé gone |
| V19 | Car SFX + audio mixing balance | 1 | Final |

**Total: 19 versions across 3-4 sessions.** Expect this range for a project of this scope.

---

## Tips from this project

- **Trust the user's perception over the math.** If they say "I feel saccadé", investigate even if FPS calculations say it should be smooth. There's always a layer (compression, motion blur, content-specific) you didn't account for.
- **One change at a time** — saves hours of back-and-forth
- **Cache aggressively** — sub-clip rendering is the expensive step
- **Frame-perfect timing only matters once you're close** — first pass approximate timing, refine later
- **Synthetic SFX is fine** — lavfi-generated SFX work for cinematic ambient projects. For action-heavy edits, real foley is better.
- **The LUT is not a magic button** — partial blend (0.40-0.50) preserves more of the source character
- **Render preview after EVERY change** — even if you're sure it works
