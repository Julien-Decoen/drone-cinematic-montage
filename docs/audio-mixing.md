# Audio Mixing — the iterative methodology

The most time-consuming and subjective phase of any drone montage. This document captures the methodology refined over 15 mix iterations on the Interlaken project (mixes I → U).

## Three principles

1. **The music dictates** the emotional bed. SFX should support, never dominate.
2. **Calibrate first, then iterate** — measure every SFX vs music loudness BEFORE tweaking.
3. **Propose options, don't guess** — give the user 2-3 mix variants per round (subtle / mid / strong) and let them pick.

## Step 1 — Categorize every plan's SFX

Per-plan SFX falls into one of 5 categories. Each has its own target volume relative to music.

| Category | Plans (example) | Target dB vs music |
|---|---|---|
| **ambient** | calm landscape, lake, opening | **-20 to -22** |
| **info** | cars, train, distinct events with story value | **-14 to -18** |
| **cascade** (climax water) | waterfall (#14 in our project) | **-18 to -25** (user-tunable) |
| **boom** | castle/dramatic reveal hit | **-10 to -12** |
| **fx** | whoosh, riser, transitions | **-14 to -18** |
| **outro** | closing ambient | **-20 to -22** |
| **wind_global** | continuous background | **-20 to -32** |

Why ambient is the quietest: a calm landscape doesn't need a featured sound. Just enough to know there IS ambient, not enough to compete with music.

Why info is louder: cars/trains/specific events carry narrative meaning, viewer expects to hear them when they see them.

## Step 2 — Measure every input

Music + every SFX file:

```python
def db(path):
    r = subprocess.run([
        "ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"
    ], capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*(-?[\d.]+)", r.stderr)
    return float(m.group(1)) if m else None

MUSIC_DB = db(MUSIC)   # reference loudness
for sfx in SFX_FILES:
    print(f"{sfx}: {db(sfx):.1f} dB")
```

ElevenLabs SFX vary wildly (-15 to -55 dB mean). Synthesized SFX (lavfi recipes) more consistent (-15 to -25 dB). Either way: **NEVER assume volume is normalized**.

## Step 3 — Compute calibration gains

```python
def gain_for(sfx, category, music_db, targets):
    target_db = music_db + targets[category]
    cur_db = db(sfx)
    g = target_db - cur_db
    return max(-40, min(22, g))     # safety cap
```

The **+22 dB cap** is critical — pushing quiet SFX too hard amplifies the noise floor.

## Step 4 — Build the mix

Each per-clip SFX entry generates one ffmpeg filter chain:

```python
filters.append(
    f"[{idx}:a]atrim=duration={dur},"
    f"afade=t=in:st=0:d=0.4,"
    f"afade=t=out:st={dur-0.4}:d=0.4,"
    f"volume={gain:+.2f}dB,"
    f"adelay={delay_ms}|{delay_ms}[s{i}]"
)
```

For SFX that should END HARD (like a finale wind that shouldn't bleed into outro), use a longer fade-out (1.5s):

```python
fout = 1.5 if (sfx == "wind_global" and is_finale) else 0.4
```

## Step 5 — Music ducking

Two approaches:
- **Static**: music at fixed level (e.g. `volume=0.60` = -3 dB) → SFX sit on top by their own calibration
- **Dynamic ducking**: music drops 6 dB when SFX plays (sidechain compression) — pro but complex in ffmpeg

We've used static throughout. The category targets above are calibrated for `music_volume=0.60`.

## Step 6 — Wind global as atmospheric glue

A continuous very-low `wind_global` layer (-30 to -36 dB vs music) under the entire film adds atmospheric cohesion. At higher levels (-20 dB) it becomes a "windy" feel; at lower (-36 dB) it's just glue.

```python
inputs += ["-stream_loop", "-1", "-i", wind_global_path]
filters.append(
    f"[{wind_idx}:a]atrim=duration={total_dur-2},"
    f"afade=t=in:st=0:d=2,afade=t=out:st={total_dur-4}:d=2,"
    f"volume={wind_gain:+.2f}dB[wind]"
)
```

## Step 7 — The iteration loop

Generate 2-3 propositions in a single call:

```python
PROPS = [
    # name           ambient info climax boom fx   outro wind
    ("L_boosted",     -8,    -4,   +2,   -4,  -4,   -8,   -22),
    ("M_music_low",  -12,    -8,   -2,   -6,  -8,  -10,   -32),  # also music vol 0.40
    ("N_balanced",   -10,    -6,    0,   -6,  -6,  -10,   -28),  # music 0.60
]
```

Output 3 MP3s + 3 4K muxes simultaneously. User picks one (or asks for next iteration in that direction).

Naming convention: alphabetic letters per iteration round (`A_subtle`, `B_strong`, `C_minimal`, then `D`, `E`, etc.). Lets you reference "we want between F and G" precisely.

## Step 8 — Special cases

### Plan needs NO SFX

User says "on veut rien sur #N" → set `sfx=None` in the timeline, skip entirely. Don't try to layer "silence" — just omit.

### One plan needs DRAMATIC drop

For the boom impact on the castle (#21), the SFX (sub bass 50Hz) needs to LAND hard. Target -10 dB (4 dB above other info SFX). The dynamic contrast IS the effect.

### SFX bleeding into next plan

Cause: fade-out too short, or wind_global layer too loud continuing past.
Fix: longer fade-out on the per-plan SFX (1.5-2s), and check wind_global level isn't masking the new plan.

### SFX inaudible despite calibration

Cause: frequency masking by music. SFX in same range as music's dominant content gets buried.
Fix: either boost SFX further (+3-6 dB above target), or apply a narrow EQ notch in the music at the SFX's center frequency. Or use sidechain ducking.

## Step 9 — Final validation: storyboard video with audio

Before re-rendering the full 4K, generate a slideshow-style validation video:

```python
# For each plan, hold a single frame for plan duration
for plan in PLANS:
    img = extract_frame(plan.t_mid)
    add_label_with_PIL(img, plan)  # show plan name, sfx, gain dB
    seg = make_video_from_image(img, plan.dur)

concat_segments → mux_with_audio_mix → preview MP4
```

This produces a 1-2 min ~12 MB MP4 with one image per plan + your audio mix. User can validate audio decisions WITHOUT waiting for 4K re-render.

See `examples/interlaken_v19.py` (mix_storyboard_final.py pattern) for the implementation.

## Step 10 — Audio-only MP3 export

For sharing the mix with collaborators or quick listening:

```bash
ffmpeg -i video.mp4 -vn -c:a libmp3lame -q:a 2 audio.mp3
```

Or rebuild the mix standalone without any video pipeline. Faster iteration when no visual change is needed.

## Reference: Interlaken project final mix (V21)

After 15 iterations:

```
Music volume:        0.60  (-3 dB from raw)
Music fade out:      at 156s (4s before main ends)
Music fade duration: 8s

Per-clip SFX (relative to music):
  ambient_alpine:    -22 dB
  flag_wind:         -20 dB (on #3 reveal)
  cars_passing_high: -18 dB (high altitude top-down)
  cars_following:    -18 dB (drone following car)
  whoosh:            -18 dB
  river_gentle:      -18 dB (active) / -22 dB (background scene)
  cascade:           -25 dB (USER CHOICE: very subtle)
  lake_sail_calm:    -18 dB
  boom:              -12 dB (climax impact)
  wind_global (finale plan): -18 dB
  outro_ambient:     -22 dB (synth recipe, not ElevenLabs)

Wind global background: -20 dB (atmospheric glue throughout)

Master volume target:  -16 dB mean
```

These numbers are the **end state**, not a starting point. Always start with the categories above and iterate.

## Bugs / fixes encountered

| Bug | Cause | Fix |
|---|---|---|
| `Input contains (near) NaN/+-Inf` on AAC encode | `volume='expr':eval=frame` produces NaN | Use `afade=curve=cub/esin` instead |
| Intermittent NaN on certain SFX/durations | Low-freq vibrato + amix combinations | Simplify recipe, remove vibrato f<0.5, add `aresample=44100` |
| sfx file at 0 bytes silently | ffmpeg returncode 0 but file empty | Add cache check `os.path.getsize(out) > 1000` after run |
| `quota_exceeded` HTTP 401 | Out of ElevenLabs credits | Plan ~15 SFX max for free tier |
