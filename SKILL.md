---
name: drone-cinematic-montage
description: Build a cinematic 3-min drone montage from a folder of clips + a music track using ffmpeg + Python. Per-clip color grading, motion smoothing, music sync, SFX layering. Output 4K MP4.
when_to_use: User has drone footage clips + a music track and wants a polished cinematic edit (single video output, ~2-4 min).
---

# Drone Cinematic Montage — Skill

Build a cinematic montage from drone clips + music using ffmpeg + Python. Battle-tested over 25+ versions on a 3-day Interlaken trip (Lac de Thoune + Brienzersee). The skill produces a 3840×2160 H.264 MP4 with per-clip grading, motion smoothing, frame-precise cuts, music sync and SFX layering.

## When to invoke this skill

Trigger phrases: "drone montage", "cinematic edit", "drone cinematic", "drone reel", "video montage from clips", "monter mes rushs drone", "faire un film aérien".

Don't invoke for:
- Single-clip processing (just use ffmpeg directly)
- Music videos with full editing (this is drone-focused)
- Heavy VFX (this is grading + cuts only)

---

## 🚀 Workflow — exactly what to do when user arrives with a new project

The skill works in **6 phases**. Run them in order. Each phase has its own validator script — don't skip them.

### Phase 1 — Bootstrap (10-15 min)

User gives you: a folder of MP4 clips + a music track. You run:

```bash
python3 scripts/bootstrap_project.py \
  --clips /path/to/clips \
  --music /path/to/music.mp3 \
  --out ~/my_project \
  --title "INTERLAKEN" \
  --subtitle "Switzerland From Above"
```

This produces:
- **Clips audit** — ffprobe table (duration, fps, D-Log detection, luma/sat)
- **Music peaks** — auto-detected RMS peaks → suggested `ACT_TRANSITIONS`
- **`my_project.py`** — pre-filled EDIT list (one plan per clip, defaults), CLIP_GRADE empty, paths wired
- **`build_mix.py`** — audio mix scaffold (optional)

Show the user the audit + peaks. Ask them to confirm or reorder before going further.

### Phase 2 — Validate the EDIT list (1 min)

```bash
python3 scripts/validate_edit.py ~/my_project/my_project.py
```

For each plan: checks `src_start + out_dur × speed ≤ source_duration`. If anything fails, **fix the EDIT list before any render** — otherwise you get silent drift (see [PITFALLS §3](docs/PITFALLS.md)).

### Phase 3 — Preview loop (5-8 min per iteration)

```bash
QUALITY=preview python3 ~/my_project/my_project.py
```

Generates a 640×360 preview in ~5-8 min. Show to user, ask **specific** questions:
- ✅ Cuts feel right? Plan #N→N+1 fluid?
- ✅ Music sync OK at ACT_TRANSITIONS?
- ✅ Color cohesion across clips?

Apply **one category** of changes per iteration. Categories: A=structure, B=timing, C=color (`CLIP_GRADE`), D=motion, E=match-cuts, F=music-sync, G=SFX, H=overlays.

After each iteration, run:
```bash
python3 scripts/audit_timings.py ~/my_project/my_project.py
```
to check cumulative cut times vs `ACT_TRANSITIONS`.

### Phase 4 — Audio mix (optional, but recommended)

If using real MP3 SFX (vs lavfi synthetic), build the audio mix as a separate script:

```bash
python3 ~/my_project/build_mix.py
```

This produces `_mix.mp3` independently of the video render. **Big advantage**: iterate SFX in 30s instead of 30 min.

### Phase 5 — 4K final render (30-45 min)

⚠ Before launching:

```bash
python3 scripts/validate_cache.py /tmp/<project_name> --quality final
```

This is THE critical step — see [PITFALLS §1](docs/PITFALLS.md). The cache silently reuses 640×360 preview clips at 4K if you don't purge.

Then:
```bash
QUALITY=final python3 ~/my_project/my_project.py
```

On M1 MacBook Pro: 30-45 min for ~22 plans with `minterpolate fps=60`. **Use AC power.**

### Phase 6 — Social distribution (10-30 min, optional)

Once master is done, user typically needs:
- YouTube thumbnails (4 variants)
- Instagram story / Reel cover (vertical 9:16, 10-15s teaser)
- Share copy for Facebook / LinkedIn / Twitter / YouTube description

→ See [docs/youtube-delivery.md](docs/youtube-delivery.md), [docs/instagram-vertical.md](docs/instagram-vertical.md) and the turn-key [docs/delivery-checklist.md](docs/delivery-checklist.md).

---

## Architecture — single Python script per project

The render script (`my_project.py`) processes the EDIT list end-to-end:

```
main()
├── 1. Generate PNG overlays (title, outro)
├── 2. process_clip × N        → render each plan to TMP/clip_NN_J.mp4
├── 3. Concat all sub-clips    → main_video.mp4
└── 4. Final encode + audio    → OUTPUT.mp4
```

**Cache strategy**: each `clip_NN_J.mp4` is named by EDIT index + sub-segment. Resumable. **But silently breaks if you switch QUALITY without purging** — use `validate_cache.py`.

---

## EDIT list — V25 tuple structure

```python
EDIT = [
    # (fname, src_start, output_dur, speed, sfx, reframe, extra)
    ("DJI_0102.MP4",  0.3,  4.0, 0.85,         "ambient", (1.0, 1.05), "hflip"),
    ("DJI_0090.MP4",  4.0,  8.0, (0.5, 0.7),   "lapping", None,        "fadeout"),
    ("DJI_0091.MP4",  2.0,  3.0, 1.0,          "boom",    None,        "reverse"),
]
```

Fields:
- `src_start` — where in source to start (s)
- `output_dur` — duration in OUTPUT timeline (s)
- `speed` — float (`0.85` = slowmo) | tuple `(s_start, s_end)` for linear ramp
- `sfx` — name in `make_sfx()` registry (or `None`)
- `reframe` — `(zoom_start, zoom_end)` Ken Burns or `None`
- `extra` — comma-separated modifiers: `"hflip"`, `"reverse"`, `"fadeout"`, or combinations like `"hflip,reverse"`

**Source consumed** = `output_dur × speed`. Validator script checks `src_start + that ≤ duration`.

---

## CLIP_GRADE — per-clip color overrides

```python
CLIP_GRADE = {
    "0084_D-00.01.21": {"lut": 0.45, "sat": 0.88, "exposure_fix": True},
}
```

- **Bright over-saturated** (greens pop too much): lower `lut` (0.35-0.45) + lower `sat` (0.78-0.88)
- **Dark plans** (luma < 85): add `gamma`: 1.08-1.18
- **Cold cast / overcast**: `exposure_fix: True` → S-curve + warm shift (preserves deep blacks)

→ Full diagnostic workflow in [docs/color-grading.md](docs/color-grading.md) and [docs/exposure-recovery.md](docs/exposure-recovery.md).

---

## Motion smoothing — minterpolate

30fps × 0.5× speed = 15fps effective → judder. Fix with motion-compensated interpolation **before** setpts:

```
minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,
setpts=2.0*PTS
```

The template applies this automatically when `src_fps < 50 AND speed < 0.9`.

→ Details in [docs/motion-smoothing.md](docs/motion-smoothing.md).

---

## SFX — two options

**A. Synthetic (`make_sfx` in template)** — fast, free, no asset folder needed. Sounds synthetic.

**B. Real MP3 (recommended for V20+)** — Pixabay + ElevenLabs `.mp3` files in `_sfx_real/`. Calibrated dB targets in external `build_mix.py`. Better fidelity.

→ For real MP3 pipeline, see [docs/sfx-real-elevenlabs.md](docs/sfx-real-elevenlabs.md) and [docs/audio-mixing.md](docs/audio-mixing.md).

---

## ⚠ Critical pitfalls (read these BEFORE the first render)

The skill has 16 documented bugs you WILL hit otherwise. Top 3:

1. **4K render produces 640×360** — cache contamination. Always run `validate_cache.py` before switching QUALITY.
2. **Cumulative drift** — source insufficient → silent clamping. Always run `validate_edit.py`.
3. **Music sync drifts after EDIT changes** — every duration tweak shifts following plans. Always run `audit_timings.py`.

→ Full bestiary in [docs/PITFALLS.md](docs/PITFALLS.md).

---

## Iteration discipline

- **Preview-first**. Never render 4K before preview is validated. Preview = 5-8 min, 4K = 30-45 min.
- **One change category per iteration**. The user can't isolate what worked if 5 things changed.
- **Cache invalidation**. When you change `src_start`, `speed`, or `CLIP_GRADE` for plan #N:
  ```bash
  find /tmp/<project> -name "clip_NN_*.mp4" -delete
  find /tmp/<project> -name "main_video.mp4" -delete
  find /tmp/<project> -name "trans_*.mp4" -delete
  ```
- **Specific validation questions**, never "ça te plaît ?". Ask "cut #N→N+1 fluide ?", "sync à 1:14 ?".

---

## Reference files in this skill

| Path | Purpose |
|---|---|
| **[SKILL.md](SKILL.md)** | This file (entry point) |
| **[PROCESS.md](PROCESS.md)** | Full A-to-Z walkthrough with music recommendations |
| **[docs/PITFALLS.md](docs/PITFALLS.md)** | ⚠ All 16 bugs documented (READ THIS) |
| **[docs/color-grading.md](docs/color-grading.md)** | Per-clip grading diagnostic |
| **[docs/exposure-recovery.md](docs/exposure-recovery.md)** | S-curve + warm shift recipe |
| **[docs/motion-smoothing.md](docs/motion-smoothing.md)** | minterpolate cookbook |
| **[docs/match-cuts.md](docs/match-cuts.md)** | Perpendicular alignment + yaw rotation matching |
| **[docs/music-sync.md](docs/music-sync.md)** | ACT_TRANSITIONS strategy |
| **[docs/sfx-layers.md](docs/sfx-layers.md)** | Synthetic SFX recipes + balance |
| **[docs/sfx-real-elevenlabs.md](docs/sfx-real-elevenlabs.md)** | Real SFX via ElevenLabs API |
| **[docs/audio-mixing.md](docs/audio-mixing.md)** | Iterative audio mixing methodology |
| **[docs/youtube-delivery.md](docs/youtube-delivery.md)** | Thumbnail / banner / title / description |
| **[docs/instagram-vertical.md](docs/instagram-vertical.md)** | Instagram 9:16 teaser |
| **[docs/delivery-checklist.md](docs/delivery-checklist.md)** | Turn-key checklist to publish a new film |
| **[scripts/bootstrap_project.py](scripts/bootstrap_project.py)** | 🚀 NEW: project starter in 1 command |
| **[scripts/validate_edit.py](scripts/validate_edit.py)** | 🛡 NEW: source capacity validator |
| **[scripts/validate_cache.py](scripts/validate_cache.py)** | 🛡 NEW: cache resolution validator |
| **[scripts/audit_timings.py](scripts/audit_timings.py)** | 🛡 NEW: cumulative cuts vs music |
| **[scripts/analyze_rotation.py](scripts/analyze_rotation.py)** | Yaw rotation rate for match cuts |
| **[scripts/analyze_sat.py](scripts/analyze_sat.py)** | Per-clip signalstats diff |
| **[templates/render_template.py](templates/render_template.py)** | 📐 V25-grade ready-to-use template |
| **[examples/interlaken_v19.py](examples/interlaken_v19.py)** | Real working script (archive, V19) |

---

## Quick reference — first-time user

```bash
# 1. Bootstrap a new project from clips + music
python3 scripts/bootstrap_project.py --clips ~/clips --music ~/music.mp3 --out ~/myproj

# 2. Validate
python3 scripts/validate_edit.py ~/myproj/my_project.py
python3 scripts/audit_timings.py ~/myproj/my_project.py

# 3. Preview (iterate until happy)
QUALITY=preview python3 ~/myproj/my_project.py

# 4. Validate cache before switching to 4K
python3 scripts/validate_cache.py /tmp/myproj --quality final

# 5. 4K master
caffeinate -i -s python3 ~/myproj/my_project.py  # with QUALITY=final
```

The whole journey from "user gives clips + music" to "4K master ready" should take **3-6 hours of wall time across 2-3 sessions** (most of which is render time you can do other things during). Without the bootstrap + validators, expect 2-3× that.
