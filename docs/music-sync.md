# Music Selection & Sync

The music track is the **structural backbone** of the montage. Acts (groups of plans) should boundary on identified music peaks. This document covers selection, identification, alignment, and adjustment workflow.

## Choosing the right track

Pick the music FIRST — the visual structure follows from it. See [PROCESS.md §1](../PROCESS.md#phase-1--music-selection) for the full style → track recommendation table.

Quick reference:
- **Mountain / landscape drone** → Cinematic Ambient (Olafur Arnalds, Max Richter, Ludovico Einaudi)
- **City / aerial reveal** → Cinematic Epic (Hans Zimmer-style, Two Steps From Hell)
- **Travel / lifestyle** → Chill electronic / Indie folk (Tycho, Bonobo, Bon Iver)
- **Sunset / golden hour** → Warm ambient (Nils Frahm, Max Cooper)
- **Action / fast cuts** → Dynamic electronic (ODESZA, Flume)

Sources: Epidemic Sound, Artlist, Musicbed (paid) · Pixabay Music, YouTube Audio Library, Bensound, Uppbeat (free/freemium).

Track requirements:
- Duration 2-4 min
- Clear emotional peaks every 30-45s (these become your Act transitions)
- Calm intro and outro 5-10s (lets the video breathe)
- Dynamic range (quiet vs loud passages) for varied visual energy


## Identify music peaks

### Manual (by ear)

Listen to the track and note timestamps where the music shifts:
- New instrument enters
- Bass drops
- Tempo / energy change
- Vocal moment

Note 4-5 major shifts for ACT transitions and a handful of internal peaks.

### Automated (RMS analysis)

```python
import subprocess, re
r = subprocess.run([
    "ffmpeg","-i","music.mp3",
    "-af","astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
    "-f","null","-"
], capture_output=True, text=True)
# Parse rms_level over time, find local maxima
```

Both methods together give the most reliable peaks.

## Use in the script

```python
ACT_TRANSITIONS = [18.0, 37.0, 74.0, 110.0, 129.0]   # major peaks (s)
INTERNAL_PEAKS  = [27.0, 54.5, 63.5, 84.0, 91.5, 100.5, 118.5, 137.5, 146.0, 154.5]
```

- `ACT_TRANSITIONS` defines where stings drop and where major plan cuts should land
- `INTERNAL_PEAKS` are for finer alignment (optional but improves rhythm)

## Aligning plan cuts to peaks

Compute cumulative output times. Each plan boundary is the sum of all previous `out_dur` (minus xfade overlaps).

```python
cum = 0.0
for i, edit in enumerate(EDIT):
    cum += edit[2]  # out_dur
    if i in [3, 7, 13, 16, 19]:  # boundaries between Acts
        print(f"Act cut after plan #{i+1}: t = {cum:.2f}")
```

Target each Act cut within **±1.5s** of the corresponding `ACT_TRANSITIONS[i]`.

If off:
- **Cut too early** (e.g. 35s vs target 37s) → extend a plan in that Act by 1-2s
- **Cut too late** (e.g. 78s vs target 74s) → shorten a plan (often the longest, by 4-5s if needed)

## Stings — automated drop at each peak

In the script, stings are mixed at `ACT_TRANSITIONS` time minus 0.8s (anticipation effect):

```python
sting_delays_ms = [int(t * 1000) - 800 for t in ACT_TRANSITIONS]
# In final mux:
sting_filters = [f"[sting:a]adelay={d}|{d},volume=0.55[st{i}]"
                 for i, d in enumerate(sting_delays_ms)]
```

A `make_sting()` boom (low sine, 1.6s) lands on each Act boundary.

## Adjusting when timeline changes

Whenever you:
- Add a new plan
- Remove a plan
- Change `out_dur` significantly
- Add/remove an xfade transition (subtracts the xfade duration from total)

→ **Recompute the cumulative times** and verify Act boundaries still land within ±1.5s of peaks.

### Quick recomputation script

```python
EDIT_DURS = [edit[2] for edit in EDIT]
TRANSITION_OVERLAPS = {12: 0.5, 19: 0.4}  # idx → xfade duration to subtract
cum = 0
print(f"{'#':>3} {'plan':<24} {'start':>8} {'end':>8}")
for i, d in enumerate(EDIT_DURS):
    overlap = TRANSITION_OVERLAPS.get(i, 0)
    cum -= overlap
    start = cum
    cum += d
    print(f"{i+1:>3} {EDIT[i][0][:24]:<24} {start:8.2f} {cum:8.2f}")
```

## Music fade-out

End of the montage:
```python
music_fade_out_st = main_dur - 4.0   # start fade 4s before main ends
# In final mux:
[1:a]afade=t=in:st=0:d=2.5,afade=t=out:st={music_fade_out_st}:d=10.0,volume=0.85[mus]
```

A 10s linear fade typically feels natural. Avoid hard cuts on the music end.

## Common pitfalls

- **Insufficient slack** — if total video duration = music duration exactly, any tiny drift creates an audible mismatch. Plan for 5-10s of post-music tail (outro + credits) where the music is in fade-out.
- **Drifting after structural changes** — adding a 5.5s clip pushes EVERYTHING after it by 5.5s. Manually re-align downstream cuts.
- **Trying to fit music to video** instead of vice versa — the music dictates. Adjust video durations to fit the music's natural rhythm.
- **Skipping the internal peaks** — even if Act boundaries are aligned, mismatched internal cuts feel "off-tempo". Worth a second pass to nudge 1-2s here and there.
