# Exposure Recovery — S-curve + Warm Shift

For underexposed cloudy / overcast clips with a cold (blue-grey) cast, naive `brightness=+0.X` lifts the entire histogram, **including the black point**, producing muddy grey shadows.

The fix is a **shadow-compressed S-curve** that lifts mids and highlights while keeping blacks anchored at 0, combined with a small warm shift to neutralize the cold cast.

## The chain

```ffmpeg
[bl]curves=master='0/0 0.05/0.02 0.20/0.27 0.50/0.62 0.80/0.88 1/1':all='0/0 1/1',
   colorbalance=bs=-0.05:bm=-0.03:bh=-0.02,
   eq=saturation=SAT:gamma=GAMMA:contrast=1.080,
   vignette=PI/5.5
```

### Curve points decoded

| Input | Output | Effect |
|---|---|---|
| 0 / 0 | Anchor at black — true blacks preserved |
| 0.05 → 0.02 | **Compresses** deep darks toward 0 (creates contrast) |
| 0.20 → 0.27 | Lifts dark mids by ~7% |
| 0.50 → 0.62 | Lifts mids by ~12% (main exposure recovery) |
| 0.80 → 0.88 | Pushes highlights up ~8% |
| 1 / 1 | Anchor at white |

The first segment (0 → 0.05 → 0.02) is the secret: it's a *compressive* slope (slope = 0.4) that drives the deepest darks BACK toward 0 even as the curve overall lifts.

Without that compression (using e.g. `0/0 0.20/0.30 ...`), the slope from 0 to 0.20 would be 1.5x → all dark pixels lifted = muddy.

### Color balance

```
colorbalance=bs=-0.05:bm=-0.03:bh=-0.02
```

- `bs` (shadows blue) = -0.05 → -5% blue in shadows (warm shadow)
- `bm` (midtones blue) = -0.03 → -3% blue in mids
- `bh` (highlights blue) = -0.02 → -2% blue in highlights

The shift is graduated: more correction in shadows (where the cold cast is most visible), less in highlights (to preserve the natural daylight feel).

### Saturation + contrast

After curves and color balance:
- `saturation` typically `1.05-1.20` (more punch since the corrected scene now has more visible color information)
- `gamma=1.08` if the clip's natural luma is below 70 (extra mid lift)
- `contrast=1.08` to retain punch after the curves opened up

## When to apply

Use `exposure_fix: True` in CLIP_GRADE when ALL of these are true:
1. **Luma is low** (YAVG < 95)
2. **Cold cast** (UAVG > 128, i.e. positive U_dev)
3. **Shadow detail is buried** (% pixels < 10 of luma == 0% or very low)
4. **Neighbors are brighter / warmer** (the clip stands out as "dark and blue" in storyboard)

## Verification — signalstats

After applying `exposure_fix`, the metrics should converge to neighbors:

```bash
ffmpeg -ss <t> -t 1 -i video.mp4 \
       -vf "scale=320:-1,signalstats,metadata=print" \
       -f null - 2>&1 | grep -E "YMIN|YAVG|UAVG|SATAVG"
```

Target:
- `YMIN` near 0 (deep blacks)
- `% pixels < 10 luma` similar to neighbors (typically 2-5%)
- `YAVG` increased by 10-20 vs raw clip
- `SATAVG` ±2 of neighbors
- `UAVG` close to 128 (no chrominance bias)

## Comparison: 3 wrong vs right approaches

### ❌ Wrong A: Brightness lift
```
eq=brightness=0.05
```
→ Lifts blacks. YMIN = 13. Greys visible everywhere.

### ❌ Wrong B: Gamma alone
```
eq=gamma=1.20
```
→ Lifts mids well but also lifts dark pixels. YMIN = 8. Slight muddy feel.

### ❌ Wrong C: Curves without shadow compression
```
curves='0/0 0.20/0.30 0.5/0.6 1/1'
```
→ Anchor at 0/0 but slope > 1 from start. YMIN = 6.8 (still lifted by linear interpolation).

### ✅ Right: S-curve with compressive head
```
curves='0/0 0.05/0.02 0.20/0.27 0.50/0.62 0.80/0.88 1/1'
```
→ Compressive segment 0→0.05 pushes dark pixels TOWARDS 0. YMIN = 0. 4% pixels < 10.

## Example results

From the Interlaken project, plan #2 (lac brumeux, overcast):

| Stage | YMIN | %<10 | %<20 | YAVG | UAVG_dev | SATAVG |
|---|---|---|---|---|---|---|
| V12 raw + ambient LUT | 0 | 1.9% | 7.5% | 79 | -2.1 | 4.5 |
| V12 + brightness=+0.05 | 13 | 0% | 1.2% | 92 | -1.8 | 4.5 |
| V12 + exposure_fix (S-curve) | 0 | 4.4% | 17.9% | 66 → 92 | 0.1 | 6.0 |

The third row preserves YMIN=0 (deep blacks like neighbors) while lifting average luma into the readable range.

## Limitations

- Doesn't recover **completely clipped** shadows (data lost in capture)
- Doesn't fix **motion blur** (separate concern)
- Adds slight chroma shift even with `colorbalance` — for extreme cold cast, may need additional `eq=gamma_b=0.95` (per-channel gamma)
