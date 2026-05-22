# Motion Smoothing — minterpolate

When playing a 30fps source at speed < 0.9×, the effective frame rate drops below 27fps → visible judder ("saccadé" in French). The fix is **motion-compensated frame interpolation** that synthesizes intermediate frames before the speed change.

## The chain (placement is critical)

```ffmpeg
[0:v]hflip,scale=W:H:flags=lanczos,
      minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,
      setpts={1/speed}*PTS,
      ...
```

**Order matters**: `minterpolate` runs on the **source frames** at their natural rate. Then `setpts` stretches them. If you swap the order, you'd interpolate already-stretched frames → garbage.

## Parameters

- `fps=60` — target framerate after interpolation. For 30fps source × 0.5× output speed = effective 30fps display rate.
- `mi_mode=mci` — Motion Compensated Interpolation (vs `blend` = simple frame blend, less smooth)
- `mc_mode=aobmc` — Adaptive Overlapped Block Motion Compensation (vs `obmc` plain — `aobmc` adapts block size to motion magnitude)
- `me_mode=bidir` — Bidirectional motion estimation (forward + backward)
- `vsbmc=1` — Variable Size Block Motion Compensation enabled

## When to apply

```python
need_interp = (src_fps_int < 50 and effective_speed < 0.9)
```

- ✅ 30fps source at 0.85x, 0.7x, 0.5x → apply
- ❌ 30fps source at 1.0x, 1.2x → no benefit
- ❌ 60fps source at 0.5x → already 30fps effective, no benefit
- ❌ Speed ramp `(0.8, 1.2)` → each sub-segment evaluated independently; only apply to sub-segments < 0.9

## Cost

`minterpolate` is **expensive**. At 4K with ~22 plans:
- Without minterpolate: ~15-20 min total
- With `fps=60`: ~30-45 min total
- With `fps=120`: ~60-90 min total (only ~5% smoother than 60, not worth it)

Use **fps=60** as the default. Only push to 120 if there's a specific judder issue not solved by 60.

## Alternative: tblend (deprecated for this use case)

```ffmpeg
tblend=all_mode=average:all_opacity=0.4
```

`tblend` averages adjacent OUTPUT frames (not source). Produces motion blur but doesn't recover frames. For 30fps → 0.5× output, you'd be averaging duplicate frames → no help.

**Conclusion**: use `tblend` only for stylized motion blur on real-time clips. For slowmo, use `minterpolate`.

## Per-clip vs per-sub-segment

When a clip has a speed ramp, `process_clip` breaks it into `n_sub` sub-segments (typically 5). Each gets its own `process_subseg` call. Evaluate `need_interp` per sub-segment:

```python
for j, (sub_src, sub_speed, sub_out, sub_rf) in enumerate(subs):
    need_interp = (src_fps_int < 50 and sub_speed < 0.9)
    process_subseg(..., motion_blur=need_interp)
```

For a `(0.6, 1.0)` ramp on 30fps source:
- Sub 0: speed ~0.62 → interp ✓
- Sub 1: speed ~0.73 → interp ✓
- Sub 2: speed ~0.80 → interp ✓
- Sub 3: speed ~0.92 → interp ✗ (>= 0.9)
- Sub 4: speed ~0.98 → interp ✗

## Verification

If the user reports "still saccadé" after applying:
1. Check the source fps — `ffprobe -show_entries stream=r_frame_rate`
2. Verify minterpolate appears in your filter chain (`echo` the chain)
3. Check effective playback speed (might be a ramp where some sub-segs are fast enough)
4. Push to `fps=120` only as last resort (or speed UP the clip to 1.0x)

## Gotchas

- `minterpolate` introduces a slight ~50-200ms delay at the START of the clip while frames are buffered. Account for this in `src_start` if you need precise sync to music.
- It can produce **ghosting** on shots with discrete moving objects against busy backgrounds (e.g. a single bird crossing trees). For these, prefer real-time playback (`speed=1.0`).
- `aobmc` requires `mc_mode=aobmc` explicitly. Default is `obmc` which is plainer.
