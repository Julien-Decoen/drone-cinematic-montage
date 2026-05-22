# drone-cinematic-montage

A Claude Code skill for building cinematic drone montages with ffmpeg.

> Battle-tested over 16 iterations on a 22-plan Interlaken montage (Switzerland drone footage, 3-day trip).

## What it does

Produces a single MP4 (preview 640×360 or final 4K 3840×2160) from a folder of drone clips and a music track, with:

- **Per-clip color grading** — LUT blend + custom saturation/gamma per clip via `CLIP_GRADE` dict
- **Exposure recovery** — S-curve + warm shift for underexposed/cold-cast clips (preserves deep blacks)
- **Motion smoothing** — motion-compensated frame interpolation (`minterpolate fps=60`) for smooth slowmo on 30fps sources
- **Form-match cuts** — perpendicular alignment between adjacent top-down shots (e.g. rails → bridge)
- **Music sync** — Act boundaries land within ±1.5s of identified music peaks
- **SFX layering** — per-clip synthetic SFX + global wind ambient + transition whooshes

## Quick start

### 1. Install as a Claude Code skill

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/<your-user>/drone-cinematic-montage.git
```

Then in any Claude Code session, ask:

> "Build a cinematic montage from the drone clips in `~/Documents/drone/MyTrip/` synced to `~/Documents/drone/MyTrip/music.mp3`"

Claude will invoke the skill and follow the workflow.

### 2. Use the script directly

```bash
# Edit the EDIT list in examples/interlaken_v16.py to point at your clips
# Then:
QUALITY=preview python3 examples/interlaken_v16.py   # ~5 min
QUALITY=final   python3 examples/interlaken_v16.py   # ~30-45 min for 4K
```

## Dependencies

- `ffmpeg` ≥ 6.0 (with libx264, `minterpolate`, `lut3d`)
- `python3` ≥ 3.10
- `Pillow` (PIL) — for title/credits PNG generation
- `opencv-python` + `numpy` — only for the optional analysis scripts (rotation/perpendicular detection)

## Architecture

Single Python script generates ffmpeg commands. Each "plan" (shot) is processed independently to a cached sub-MP4, then concatenated. Title/outro overlays applied as a second pass. Audio mixed in the final encode.

```
script.py
├── EDIT list           — ordered list of plans (file, src_start, out_dur, speed, sfx, reframe)
├── CLIP_GRADE          — per-clip color overrides (lut, sat, gamma, exposure_fix)
├── ACT_TRANSITIONS     — music peak timestamps for boundary alignment
├── process_clip()      — render a single plan (with sub-segments for speed ramps)
├── process_outro()     — outro with PNG overlay baked
├── render_xfade_pair() — xfade transition between two clips
└── main()              — orchestrator + final encode
```

Cache lives in `/tmp/<project_name>/clip_NN_J.mp4`. Resumable — re-running picks up where it left off.

## Documentation

- **[PROCESS.md](PROCESS.md)** — **Full A-to-Z workflow** with music recommendations, color grading strategy, motion handling, SFX layers, audio mixing, iteration loop, and 4K render. Start here.
- [SKILL.md](SKILL.md) — Detailed skill instructions (the file Claude Code reads)
- [docs/music-sync.md](docs/music-sync.md) — Music selection + sync to peaks
- [docs/color-grading.md](docs/color-grading.md) — Per-clip CLIP_GRADE strategy
- [docs/exposure-recovery.md](docs/exposure-recovery.md) — S-curve + warm shift for underexposed clips
- [docs/motion-smoothing.md](docs/motion-smoothing.md) — minterpolate fps=60 for anti-saccadé
- [docs/match-cuts.md](docs/match-cuts.md) — Form match cuts (perpendicular alignment, rotation matching)
- [docs/sfx-layers.md](docs/sfx-layers.md) — Synthetic SFX recipes + audio mixing balance
- [docs/workflow.md](docs/workflow.md) — Iteration loop details

## Reference project

`examples/interlaken_v16.py` is the production script from a 3-day Interlaken trip montage:
- 22 plans + outro + credits = 181s total
- ~50 GB of source footage from a DJI drone
- Music: Nastelbom — *Cinematic Ambient*
- 16 iterations over ~3 sessions before locking V16

## Tradeoffs

- **Synthetic SFX only** — no royalty-free audio integration. Add manually if you want real sounds.
- **Single-frame title overlay** — no animated text (only fade in/out)
- **No GPU acceleration** — pure libx264 CPU encode. Could be ~3-5× faster with VideoToolbox on macOS or NVENC on NVIDIA, but quality consistency matters more for this workflow.

## License

MIT — see [LICENSE](LICENSE)

## Credits

Built collaboratively with Claude Code during the Interlaken project, May 2026.
