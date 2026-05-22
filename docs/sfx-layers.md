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

### `cars_far` — distant traffic for high-altitude top-down
```
anoisesrc=c=brown:a=0.5,lowpass=f=350,tremolo=f=0.4:d=0.3,volume=0.40
+ sine=f=70,vibrato=f=0.2:d=0.3,volume=0.18
amix
```
Use when drone is >50m above road. Cars look small. Sound is filtered rumble.

### `cars_mid` — audible engines for medium-altitude
```
anoisesrc=c=brown:a=0.6,lowpass=f=700,tremolo=f=0.7:d=0.4,volume=0.45
+ sine=f=110,vibrato=f=0.4:d=0.4,volume=0.24
+ sine=f=180,vibrato=f=0.6:d=0.5,volume=0.16
amix
```
Use when drone is 20-50m. Engines start being audible distinctly.

### `cars_close` — defined road noise (optional — sometimes too much)
```
anoisesrc=c=pink:a=0.7,bandpass=f=600:w=900,tremolo=f=1.0:d=0.5,volume=0.55
+ sine=f=140,vibrato=f=1.2:d=0.5,volume=0.30
+ sine=f=210,vibrato=f=2.0:d=0.6,volume=0.20
amix
```
Use sparingly — for low-altitude road shots only. Often too aggressive for cinematic mood.

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

## Audio mixing — the balance methodology

Without normalization, SFX recipes have wildly different output levels — cascade dominates while ambient is inaudible.

### Step 1 — Normalize per-recipe target volumes

Each SFX recipe's final `amix` output should fall within a target range:

| Recipe | Target sum volume | Reasoning |
|---|---|---|
| `cascade_fade` | 0.85–1.0 | Climax — allowed to be slightly louder |
| `whoosh` | 0.7–0.8 | Quick burst, present without spiking |
| `boom` | 1.0–1.5 | Single impulse, can be punchy |
| `ambient` | 0.5–0.6 | Background — boosted from naive 0.16 |
| `cars_far` / `cars_mid` | 0.5–0.6 | Layered traffic, not dominant |
| `birds` / `train` / `lapping` / `sail` | 0.5–0.7 | Normalized |
| `riser` / `outro_ambient` | 0.7–1.0 | Climactic / closing |
| `wind_global` | 0.30 | Subtle continuous |

If you find your cascade is too loud vs ambient, reduce the cascade `volume=` inside its recipe (not in the final mix — that would affect everything).

### Step 2 — Final mix volumes

In the final `afilter` of your script:

```python
afilter = (
    f"[1:a]afade=t=in:st=0:d=2.5,"
    f"afade=t=out:st={music_fade_out}:d=10.0,"
    f"volume=0.85[mus];"                          # music = 0.85
    f"[2:a]volume=0.50[main_sfx_v];"              # all per-clip SFX combined = 0.50
    f"[3:a]volume=0.55,adelay={main_dur*1000}|{main_dur*1000}[outro_sfx_v];"
    f"[mus][main_sfx_v][outro_sfx_v]amix=inputs=3...[base]"
    + sting_chain                                  # stings 0.55
    + transfx_chain                                # transition SFX 0.70
    + f";[wind_idx:a]volume=0.65[wind]"            # wind_global 0.65
    + f";[match_idx:a]adelay=...,volume=0.55[matchwh]"  # match whoosh 0.55
    + ...
)
```

### Step 3 — Validate by ear

Render preview, listen with **good speakers or headphones** (not laptop speakers — they miss bass and exaggerate mids). Iterate:
- Cascade still too loud? Reduce its recipe volumes
- Ambient still inaudible? Boost recipe volume OR increase main_sfx mix to 0.60
- Music drowning out everything? Lower music to 0.75

### Balance debugging cheatsheet

| Symptom | Likely cause | Fix |
|---|---|---|
| Cascade SFX too loud vs others | Cascade recipe sums to 5.0+ | Cut each layer's `volume=` by 50% |
| Plan ambient inaudible | Ambient recipe sums to 0.16 (defaults) | Boost layers to 0.30+0.20 = 0.50 |
| Whoosh blows the meter | `volume=1.3` in recipe | Drop to 0.75 |
| Boom doesn't impact | Outro SFX delay misaligned | Verify `adelay=int(main_dur*1000)` |
| SFX inaudible vs music | Music too loud OR main_sfx too quiet | Music 0.85→0.75 OR main_sfx 0.50→0.65 |
| Cuts feel "missing" | No match_whoosh on form cuts | Add 0.5s whoosh at cut time, volume=0.55 |

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
