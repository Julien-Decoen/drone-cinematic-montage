---
name: drone-cinematic-montage
description: Build a cinematic 3-min drone montage from a folder of clips + a music track using ffmpeg + Python. Per-clip color grading, motion smoothing, beat-precise music sync, SFX layering, multi-aspect delivery. Output 4K MP4.
when_to_use: User has drone footage clips + a music track and wants a polished cinematic edit (single video output, ~2-4 min).
---

# Drone Cinematic Montage — Skill (v3)

Build a cinematic montage from drone clips + music using ffmpeg + Python. Battle-tested over 25+ versions on a 3-day Interlaken trip. V3 adds the **pro-grade pipeline**: ingest/DIT, culling, post-stabilization, beat-precise sync, LUFS mastering, L/J-cuts, multi-aspect delivery.

## When to invoke this skill

Trigger phrases: "drone montage", "cinematic edit", "drone cinematic", "drone reel", "video montage from clips", "monter mes rushs drone", "faire un film aérien".

Don't invoke for:
- Single-clip processing (just use ffmpeg directly)
- Music videos with full editing (this is drone-focused)
- Heavy VFX (this is grading + cuts only)

---

## 🚀 Workflow — exactly what to do when user arrives with a new project

The skill works in **9 phases**. Run them in order. Each phase has its own script or validator.

### Phase 0 — Ingest / DIT (post-shoot, before deleting the SD card!)

```bash
python3 scripts/ingest.py \
  --source /Volumes/DJI_SD \
  --out ~/Documents/drone/MyProject \
  --project INT --day 1 \
  --backup /Volumes/ExternalSSD/drone_backup
```

→ Copies to `01_masters/`, mirrors to backup (3-2-1), generates 240p proxies in `02_proxies/`, writes `metadata.json`, renames files deterministically.

→ [docs/pro-workflow.md#preprod-dit](docs/pro-workflow.md)

### Phase 0.5 — Cull / select (1-5 star rating)

```bash
python3 scripts/cull.py ~/Documents/drone/MyProject/02_proxies/
# rate each clip 0-5 interactively
python3 scripts/cull.py ~/Documents/drone/MyProject/02_proxies/ --filter 4 --copy ~/selects/
```

→ Reduces 200 clips → 30-50 "selects" → starting point for the EDIT list.

### Phase 1 — Stabilization (optional but recommended)

```bash
python3 scripts/stabilize.py ~/selects/ --smoothing 30
# → ~/selects/stabilized/  (use as CLIPS in render template)
```

→ vidstab 2-pass kills micro-jitter that DJI gimbal misses. Adds ~1× real-time per clip.

### Phase 2 — Bootstrap project

```bash
python3 scripts/bootstrap_project.py \
  --clips ~/selects/stabilized/ \
  --music ~/music.mp3 \
  --out ~/myproj \
  --title "MYTITLE" \
  --subtitle "Subtitle From Above"
```

→ Probes all clips (D-Log detection, fps, luma), analyses music RMS peaks, generates pre-filled `my_project.py` + audit table + suggested `ACT_TRANSITIONS`.

### Phase 3 — Beat sync (when music has clear beats)

```bash
python3 scripts/beat_sync.py ~/music.mp3 --script ~/myproj/my_project.py
# review the suggested snaps, then:
python3 scripts/beat_sync.py ~/music.mp3 --script ~/myproj/my_project.py --apply
```

→ librosa beat track → snap each cut to nearest beat (configurable max delta). 3× more impactful than RMS-peak sync.

### Phase 4 — Validate the EDIT list

```bash
python3 scripts/validate_edit.py ~/myproj/my_project.py
python3 scripts/audit_timings.py  ~/myproj/my_project.py
```

→ Catches source-insufficient plans BEFORE wasting 30 min on a render. See [PITFALLS §3](docs/PITFALLS.md).

### Phase 5 — Preview loop (5-8 min per iteration)

```bash
QUALITY=preview python3 ~/myproj/my_project.py
```

Apply **one category** of changes per iteration: A=structure, B=timing, C=color (`CLIP_GRADE`), D=motion, E=match-cuts, F=music-sync, G=SFX, H=overlays.

Optional: use **reference-based grading** to match a look:
```bash
python3 scripts/reference_grade.py ~/reference_still.jpg --strength 0.4
# → reference_still_grade.cube → plug into LUT_SRC in my_project.py
```

### Phase 6 — Audio mix (external)

If using real MP3 SFX:
```bash
python3 ~/myproj/build_mix.py
```

For L-cut/J-cut polish (audio bridges between cuts):
```bash
python3 scripts/lcut_jcut.py ~/myproj/my_project.py \
  --sfx-dir ~/_sfx_real/ --mode mixed --overlap 0.5
# → _lcut_jcut_mix.mp3 (use instead of standard mix)
```

### Phase 7 — 4K final render (30-45 min)

⚠ Before launching:
```bash
python3 scripts/validate_cache.py /tmp/<project_name> --quality final
```

THE critical step — see [PITFALLS §1](docs/PITFALLS.md). Cache silently reuses 640×360 preview clips at 4K otherwise.

Then:
```bash
QUALITY=final python3 ~/myproj/my_project.py
```

### Phase 8 — Mastering (LUFS + multi-aspect)

```bash
# Audio mastering for streaming platforms
python3 scripts/master_audio_lufs.py master.mp4
# → master_lufs.mp4 (-14 LUFS, YouTube/Spotify normalized)

# Multi-aspect deliverables
python3 scripts/multi_aspect_export.py master_lufs.mp4
# → master_lufs_multi/{9x16, 1x1, 4x5}.mp4
```

### Phase 9 — Social distribution (optional)

Thumbnails, story videos, share copy — captured in templates (TODO: thumbnails_template.py + story_reel_template.py).

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

Cache strategy: each `clip_NN_J.mp4` is named by EDIT index + sub-segment. Resumable. **But silently breaks if you switch QUALITY without purging** — use `validate_cache.py`.

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
- `speed` — float (`0.85` = slowmo) | tuple `(s_start, s_end)` for linear ramp (or use `bezier_ramp.py` for cubic ease, opt-in)
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
- **Match a reference**: generate a LUT with `reference_grade.py` and assign to `LUT_SRC` globally

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

**B. Real MP3 (recommended for V20+)** — Pixabay + ElevenLabs `.mp3` files in `_sfx_real/`. Calibrated dB targets in external `build_mix.py`. Better fidelity. Combine with `lcut_jcut.py` for polished audio bridges.

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
| **[docs/pro-workflow.md](docs/pro-workflow.md)** | 🆕 v3 — 9 pro-grade steps explained |
| **[docs/color-grading.md](docs/color-grading.md)** | Per-clip grading diagnostic |
| **[docs/exposure-recovery.md](docs/exposure-recovery.md)** | S-curve + warm shift recipe |
| **[docs/motion-smoothing.md](docs/motion-smoothing.md)** | minterpolate cookbook |
| **[docs/match-cuts.md](docs/match-cuts.md)** | Perpendicular alignment + yaw rotation matching |
| **[docs/music-sync.md](docs/music-sync.md)** | ACT_TRANSITIONS strategy |
| **[docs/sfx-layers.md](docs/sfx-layers.md)** | Synthetic SFX recipes + balance |
| **scripts/** | All utility scripts (see below) |
| **[templates/render_template.py](templates/render_template.py)** | V25-grade ready-to-use template |
| **[examples/interlaken_v19.py](examples/interlaken_v19.py)** | Real working script (archive, V19) |

### Scripts (utilitaires)

**v2 — bootstrap + validators:**
- [`scripts/bootstrap_project.py`](scripts/bootstrap_project.py) — 🚀 project starter in 1 command
- [`scripts/validate_edit.py`](scripts/validate_edit.py) — 🛡 source capacity validator
- [`scripts/validate_cache.py`](scripts/validate_cache.py) — 🛡 cache resolution validator
- [`scripts/audit_timings.py`](scripts/audit_timings.py) — 🛡 cumulative cuts vs music

**v3 — pro pipeline:**
- [`scripts/ingest.py`](scripts/ingest.py) — 📁 DIT: backup + proxies + naming + metadata
- [`scripts/cull.py`](scripts/cull.py) — ⭐ 1-5 star rating workflow
- [`scripts/stabilize.py`](scripts/stabilize.py) — 🎯 vidstab 2-pass post-stab
- [`scripts/beat_sync.py`](scripts/beat_sync.py) — 🎵 librosa beat-precise sync
- [`scripts/reference_grade.py`](scripts/reference_grade.py) — 🎨 reference image → CUBE LUT
- [`scripts/master_audio_lufs.py`](scripts/master_audio_lufs.py) — 🔊 LUFS mastering for streaming
- [`scripts/lcut_jcut.py`](scripts/lcut_jcut.py) — 🔗 L/J-cut audio bridging
- [`scripts/multi_aspect_export.py`](scripts/multi_aspect_export.py) — 📐 1 master → N aspects (opt-in)
- [`scripts/bezier_ramp.py`](scripts/bezier_ramp.py) — ⚠ cubic ease speed ramp (opt-in, perf warning)
- [`scripts/analyze_rotation.py`](scripts/analyze_rotation.py) — Yaw rotation rate for match cuts
- [`scripts/analyze_sat.py`](scripts/analyze_sat.py) — Per-clip signalstats diff

---

## Quick reference — first-time user end-to-end

```bash
# Phase 0: DIT (after shoot)
python3 scripts/ingest.py --source /Volumes/DJI_SD --project NOR --out ~/Drone/Norway --day 1

# Phase 0.5: cull
python3 scripts/cull.py ~/Drone/Norway/02_proxies/
python3 scripts/cull.py ~/Drone/Norway/02_proxies/ --filter 4 --copy ~/Drone/Norway/03_selects/

# Phase 1: stabilize
python3 scripts/stabilize.py ~/Drone/Norway/03_selects/

# Phase 2: bootstrap
python3 scripts/bootstrap_project.py --clips ~/Drone/Norway/03_selects/stabilized/ \
  --music ~/music.mp3 --out ~/Drone/Norway/project \
  --title "NORWAY" --subtitle "Fjords From Above"

# Phase 3-4: beat sync + validate
python3 scripts/beat_sync.py ~/music.mp3 --script ~/Drone/Norway/project/my_project.py
python3 scripts/validate_edit.py ~/Drone/Norway/project/my_project.py

# Phase 5: preview loop
QUALITY=preview python3 ~/Drone/Norway/project/my_project.py
# iterate…

# Phase 7: 4K master
python3 scripts/validate_cache.py /tmp/project --quality final
QUALITY=final python3 ~/Drone/Norway/project/my_project.py

# Phase 8: mastering
python3 scripts/master_audio_lufs.py master.mp4
python3 scripts/multi_aspect_export.py master_lufs.mp4
```

---

## Dependencies

Core (required):
- `ffmpeg ≥ 6.0` with `libx264`, `minterpolate`, `lut3d`, `vidstabdetect/transform`
- `python3 ≥ 3.10`
- `Pillow` — title PNG generation

v3 optional (per-script):
- `librosa` — beat_sync.py
- `scikit-learn` + `numpy<2` — reference_grade.py
- `opencv-python` + `numpy<2` — timer overlay / saliency reframing

Install all:
```bash
pip install pillow librosa scikit-learn "numpy<2" opencv-python
```

The whole journey from "user gives clips + music" to "4K master + multi-platform deliverables" should take **3-6 hours of wall time across 2-3 sessions** with v3 (most of which is render time). v2 was 6-12h. v1 was 12-25h. ROI is real.
