# Workflow

End-to-end iterative process to build a drone cinematic montage.

## 0. Discovery (with the user)

Before writing any code:

1. **List source clips** — `ls "<clips_folder>"/*.MP4` + `ffprobe` each for duration, fps, codec
2. **Get the music track** — duration, peaks (RMS analysis or by ear)
3. **Get the LUT** (optional) — typically `.cube` file
4. **Ask the user**:
   - Target duration (suggest 2-3 min for ambient/cinematic; longer feels indulgent)
   - Theme/mood (chill, dramatic, dynamic)
   - Specific clips that MUST be included (the hero shots)
   - Specific clips that are throwaways
   - Whether they want title overlay + credits

## 1. Initial EDIT proposal

Build a first EDIT list:
- 5-7 plans per "act", 4-5 acts
- Speeds default to 0.7-1.0× (no extreme slowmo at first iter)
- Outro 5-10s with credit overlay
- Total target ≈ music duration + 10-15s tail

Tag suspect clips for later attention:
- Underexposed → mark for `exposure_fix`
- Bright greens → mark for sat reduction
- Heavy motion blur intros → push `src_start` later

## 2. First render — preview

```bash
QUALITY=preview python3 script.py
```

640×360, ~5-8 min. Use `caffeinate -i -s -w $PID` if unattended.

## 3. Storyboard for review

Generate a 4×N grid of thumbnails labeled with plan #. Highlight changed plans with a colored band. Show to user.

```python
# Use the FRAMES list with t = midpoint of each plan in the output timeline
```

## 4. Iteration categories (one at a time)

Don't mix categories. User can't isolate what worked if 5 things changed.

### Category A — Order / structure
Reorder plans, add/remove plans, change which clip is which act. Big timeline shifts. **Run music sync verification after.**

### Category B — Per-clip timing
Change `src_start`, `out_dur`, `speed`. Affects pacing within an act.

### Category C — Color grading
Update `CLIP_GRADE` entries. Use signalstats analysis to be objective:

```bash
ffmpeg -ss <t> -t 1 -i video.mp4 \
       -vf "scale=640:-1,signalstats,metadata=print" \
       -f null - 2>&1 | grep -E "YAVG|UAVG|VAVG|SATAVG"
```

Compare neighbors. Target ±2 SAT delta between adjacent plans.

### Category D — Motion smoothing
Add `minterpolate=fps=60` for slow clips (`speed < 0.9` on 30fps source).

### Category E — Match cuts
Find perpendicular / matching frames between adjacent clips. See [match-cuts.md](match-cuts.md).

### Category F — Music sync
Recompute cumulative cut times. Adjust 1-2 plan durations to land each Act boundary within ±1.5s of `ACT_TRANSITIONS`. See [music-sync.md](music-sync.md).

### Category G — SFX
Per-clip `sfx` strings + global wind/whoosh layers. See [sfx-layers.md](sfx-layers.md).

### Category H — Title / outro design
PNG positioning, fade timings, text content. Use `_draw_plain()` for no-shadow text.

## 5. Re-preview after each category

Same loop:
1. Edit
2. Delete impacted cache (`rm /tmp/<project>/clip_NN_*.mp4` for changed plans)
3. `QUALITY=preview python3 script.py`
4. Generate storyboard
5. Show to user, ask **specific** validation questions

## 6. 4K final

Only after preview is fully validated.

```bash
rm -rf /tmp/<project>/   # fresh 4K cache (preview clips at 640×360 can't be reused)
caffeinate -i -s python3 -u script.py  # with QUALITY=final env var
```

ETA at 4K with `minterpolate fps=60` on ~16 of 22 plans: **30-45 min**.

## 7. Cleanup

After delivery:
- Move final MP4 out of `/tmp/`
- Optionally archive the script + `EDIT/CLIP_GRADE` snapshot as `script_locked.py`
- Don't delete `/tmp/<project>/` immediately — user may ask for one more tweak

## Versioning

Use `interlaken_v1.py` → `interlaken_v2.py` etc. (not in-place edits). This lets the user diff iterations and recover any version. Each version's `TMP` dir name is also versioned so caches don't conflict.

## When to push back on the user

- They want 100+ second slowmo intro → boring, suggest 4-6s
- They want a single LUT applied uniformly → won't work across mixed-lighting clips
- They want music + visuals to "just match without re-syncing" after a duration change → math doesn't allow it
- They want 4K render before validating preview → almost always wastes 30+ min

Be honest about tradeoffs (e.g. minterpolate cost vs smoothness).
