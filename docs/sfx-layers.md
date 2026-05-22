# SFX Layers

All SFX in this skill are **synthesized via ffmpeg lavfi** — no external audio files. Trade-off: 100% reproducible, zero licensing, but somewhat artificial.

## Three layers of SFX

```
┌─────────────────────────────────────────────────────────────┐
│ GLOBAL LAYER                                                │
│   wind_global — continuous subtle pink noise (entire timel) │
├─────────────────────────────────────────────────────────────┤
│ PER-CLIP LAYER                                              │
│   ambient / lapping / birds / train / cascade / ...         │
│   one per EDIT entry, duration matches the plan             │
├─────────────────────────────────────────────────────────────┤
│ TRANSITION LAYER                                            │
│   match_whoosh (form cuts) / sting boom (Act transitions)   │
│   single short burst at specific timestamps                 │
└─────────────────────────────────────────────────────────────┘
```

All three mix into the music bed in the final encode.

## Per-clip SFX recipes

### `ambient` — dual sine drone (neutral background)
```
sine=f=110:d=N,sine=f=165:d=N
[0]volume=0.10[a];[1]volume=0.06[b];
[a][b]amix,afade in/out
```

### `lapping` — water lapping (slow filtered pink noise)
```
anoisesrc=c=pink:a=0.45,lowpass=f=900,tremolo=f=0.8:d=0.6,volume=0.50
```

### `birds` — chirps (dual sine + irregular tremolo)
```
sine=f=2400 + sine=f=3200
[0]tremolo=f=7:d=0.95,vibrato=f=5:d=0.5,bandpass=f=2600:w=2000,volume=0.30
[1]tremolo=f=11:d=0.85,vibrato=f=8:d=0.6,bandpass=f=3200:w=1200,volume=0.18
```

### `train` / `train_whistle` — low rumble + sine whistle
```
# train:
sine=f=160,vibrato=f=0.6,lowpass=f=350,volume=0.6

# train_whistle (V16): rumble + whistle bursting at clip mid
sine=f=160[rumble] + sine=f=750[whistle starts at t=mid]
```

### `whoosh` — bandpass pink noise burst
```
anoisesrc=c=pink:a=0.55,bandpass=f=900:w=700,afade-in 0.05s,afade-out 0.45s,volume=1.3
```

### `cascade_fade` — water wash + rumble + droplets (with mid-clip fade)
```
[wash:  noisesrc=white:a=0.65,bandpass=2000:w=2000]
[bass:  sine=45,volume=1.8]
[deepbass: sine=30,volume=1.2]                              # V16 addition
[drops: noisesrc=pink:a=0.30,highpass=4000,volume=0.30]     # V16 addition
amix all 4 → fade out at 40% of dur over 35%
```

### `boom` — sub bass swell (for act transitions)
```
sine=f=50,volume=3.0,afade in 0.02s,afade out from 20% over 75%
```

### `riser` — accelerating bass + high noise (for ramp-up endings)
```
sine=f=80,vibrato=f=0.3,volume='0.35+t*0.020':eval=frame  # bass swells
noisesrc=white:a=0.40,highpass=1000,volume='0.10+t*0.040':eval=frame  # noise riser
amix both
```

### `outro_ambient` — warm drone bass + footsteps + light wind
```
sine=70 [bass1] + sine=110[bass2] + noisesrc=brown:a=0.4 [steps]
amix → fade in 1.0s, fade out 1.5s
```

## Global layer — wind_global

Mixed at the FINAL encode level (not per-clip).

```python
make_sfx("wind_global", total_full_duration, "wind_global.aac")
# Then in afilter:
"[wind_idx:a]volume=0.65[wind]"
"[base][wind][stings][transfx][matchwh]amix=inputs=5:duration=longest:normalize=0"
```

Volume 0.65 of an internally-attenuated source = subtle background presence. Adjust if user complains.

## Transition layer — match_whoosh

For form match cuts, a single whoosh peaks at the cut moment:

```python
make_sfx("whoosh", 0.6, "match_whoosh.aac")
match_cut_t = sum(e[2] for e in EDIT[:cut_idx])  # cumulative time at cut
mw_delay_ms = int(max(0, match_cut_t - 0.3) * 1000)  # peak 0.3s into the SFX
# In afilter:
f"[match_idx:a]adelay={mw_delay_ms}|{mw_delay_ms},volume=0.55[matchwh]"
```

Volume 0.55 = present but not dominant.

## Volume reference table

For the final mix:

| Layer | Volume (in afilter) | Notes |
|---|---|---|
| Music | 0.85 | Primary track |
| Main SFX (per-clip concat) | 0.28 | Already attenuated in each SFX recipe |
| Outro SFX | 0.55 | Delayed to outro start |
| Act stings (boom) | 0.55 | 5 hits per montage |
| Wind global | 0.65 | (internal volume in make_sfx already 0.18) |
| Match whoosh | 0.55 | Single hit |
| Transition SFX (xfade) | 0.70 | Per transition |

## Adding a new SFX recipe

1. Add a new `if sfx_type == "name":` branch in `make_sfx()`
2. Use `anoisesrc` for noise-based + `sine` for tonal
3. Apply `bandpass` / `lowpass` / `highpass` for shaping
4. Add `tremolo` / `vibrato` for movement
5. Always finish with `afade in` (0.05-0.5s) + `afade out` (0.5-1.0s)
6. Adjust `volume` to balance against other layers

Test by exporting just that SFX:
```bash
python3 -c "
from script import make_sfx
make_sfx('your_type', 5.0, '/tmp/test.aac')
"
ffplay /tmp/test.aac
```

## Common balance issues

- **Too much wind background** → users perceive "noise" instead of atmosphere. Drop `volume` for `wind_global` to 0.45-0.50.
- **Whoosh too loud** → distracts from cut. Drop to 0.40.
- **Sting overpowers music** → reduce sting volume to 0.40, or delay sting by 100ms more.
- **SFX layers cancel each other** → if everything is at similar frequencies, sum is muddy. Diversify (low bass + mid + sparkle), don't stack same range.
