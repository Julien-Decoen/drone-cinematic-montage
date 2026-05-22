# Color Grading

Per-clip overrides via `CLIP_GRADE` dict + a global baseline.

## Global baseline

```python
LUT_STRENGTH = 0.50    # how much the LUT influences vs. unprocessed
SAT_MULT     = 0.90    # global saturation pull (slight desaturation for natural look)
CONTRAST     = 1.05    # subtle contrast boost
```

These are the defaults when no `CLIP_GRADE` entry matches.

## LUT blend chain

```ffmpeg
scale=W:H:flags=lanczos,
split[a][b];
[b]lut3d=LUT[lb];
[a][lb]blend=all_expr='A*(1-strength)+B*strength'[bl];
[bl]eq=brightness=0:contrast=CONTRAST:saturation=SAT_MULT:gamma=GAMMA,
vignette=PI/5.5
```

The `blend` partial application lets you dial LUT influence from 0 to 1. At 0.50, the LUT does half the work; the rest is the raw source.

## Per-clip overrides

```python
CLIP_GRADE = {
    "filename_substring": {
        "lut":  0.45,
        "sat":  1.10,
        "gamma": 1.08,
        "exposure_fix": True,
    },
}
```

Match by filename **substring** — typically the `_D-MM.SS.MMM-...` segment which uniquely identifies a clip.

## Diagnostic workflow

When a plan looks "off" compared to neighbors:

### 1. Measure objectively

```bash
ffmpeg -ss <t> -t 1 -i video.mp4 \
       -vf "scale=640:-1,signalstats,metadata=print" \
       -f null - 2>&1 | grep -oE 'lavfi\.signalstats\.(YAVG|UAVG|VAVG|SATAVG)=[\d.]+' | sort -u
```

Or in Python:
```python
import subprocess, re
def stats(mp4, t):
    r = subprocess.run([
        "ffmpeg","-ss",str(t),"-t","1","-i",mp4,
        "-vf","scale=320:-1,signalstats,metadata=print",
        "-f","null","-"
    ], capture_output=True, text=True)
    e = r.stderr
    y = re.findall(r"YAVG=([\d.]+)", e)
    s = re.findall(r"SATAVG=([\d.]+)", e)
    return float(y[len(y)//2]), float(s[len(s)//2])
```

Run on each plan + neighbors. Plot or print as a table.

### 2. Identify outliers

- **SAT outliers**: plan SAT > neighbors+5 → reduce `sat`; plan SAT < neighbors-3 → increase `sat`
- **Luma outliers**: plan Y < 70 → add `gamma=1.10-1.18`; plan Y > 130 (overexposed) → reduce LUT or add slight contrast pull
- **U_dev outliers** (chrominance):
  - U_dev > +8 → too teal/blue, reduce LUT or add `colorbalance bs/m/h positive`
  - U_dev < -8 → too warm/orange, reduce LUT or add `colorbalance negative`

### 3. Apply override

Edit `CLIP_GRADE`. **Delete the impacted cache file**:
```bash
rm /tmp/<project>/clip_<idx>_*.mp4
```

Re-render. Re-measure. Iterate.

## Per-clip sat reference table

For mixed Swiss alpine footage (varied conditions), starting point:

| Scene type | lut | sat | gamma | notes |
|---|---|---|---|---|
| Cloudy lake (overcast, cold) | 0.45 | 1.10 | 1.0 | + `exposure_fix: True` |
| Bright green field aerial | 0.40-0.45 | 0.80-0.85 | 1.0 | reduce greens punch |
| Misty mountains | 0.50 | 0.90 | 1.0 | keep neutral |
| Dark forest / cliff face | 0.50 | 0.95 | 1.08 | gamma lift for shadows |
| Lake at golden hour | 0.50 | 1.00 | 1.0 | LUT does the work |
| Urban / train station (mixed) | 0.45 | 0.85 | 1.0 | balance against vegetation |
| Reflection / glassy water | 0.50 | 0.90 | 1.0 | preserve highlights |
| Snowy peaks | 0.40 | 0.85 | 1.0 | avoid yellow cast from LUT |

These are **starting points**. Iterate based on neighbors.

## Anti-patterns

- **Boosting brightness on dark clips** → grey blacks. Use `gamma` or `curves` instead.
- **Increasing contrast to fix saturation** → unrealistic, looks like a TV demo. Adjust sat directly.
- **Lifting LUT strength uniformly to "punch"** → over-stylizes. Use sat/contrast for individual plans.
- **One LUT for all** → fails on mixed lighting. Always layer per-clip overrides.

## Tool: signalstats analysis script

See [scripts/analyze_sat.py](../scripts/analyze_sat.py) — outputs a comparison table for any subset of plans.
