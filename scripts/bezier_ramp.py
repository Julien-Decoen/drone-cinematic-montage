#!/usr/bin/env python3
"""bezier_ramp.py — Render a single clip with a cubic ease-in-out speed ramp.

⚠ PERFORMANCE WARNING ⚠
The bezier ramp uses ffmpeg `setpts` with a non-linear expression that requires
the decoder to compute new PTS per frame. On 4K sources this can be 2-3× slower
than the linear ramp used by render_template.py. On lower-end machines (or M1
Air), expect noticeable lag during render. Test on ONE clip first before
applying to your full montage.

This is an OPT-IN alternative to the linear ramp `(s_start, s_end)` in EDIT.
For most cases, a constant speed (= average of the ramp) looks smoother and
renders 3× faster.

Usage:
    # Test on one clip
    python3 bezier_ramp.py input.mp4 output.mp4 --s-start 1.0 --s-end 2.0 --duration 4.0

    # The output is one MP4 you'd substitute for a single clip_NN_J.mp4
    # in the render_template.py cache.

Math (cubic ease-in-out):
    Given t in [0,1], speed(t) = s_start + (s_end - s_start) * smooth(t)
    where smooth(t) = 3t² - 2t³  (Hermite basis, continuous derivative at 0 and 1)
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def build_setpts_expr(s_start: float, s_end: float, duration: float) -> str:
    """Build a setpts expression with cubic ease-in-out.

    The integral of 1/speed(t) gives the playback time mapping.
    For smooth(t) = 3t² - 2t³, no closed-form ∫ 1/(a + b·smooth(t)) dt that's clean.

    Pragmatic approach: piecewise approximation with N sub-segments where each
    sub-segment uses a CONSTANT setpts. This gives ~10-15 discrete steps but
    visually much smoother than a 5-sub linear ramp because the speed CHANGES
    follow a cubic, not a linear, curve.

    Actually for the simplest pure-ffmpeg approach we can use setpts with t
    (frame time) as input and an expression. ffmpeg's setpts supports `T`
    (input PTS in seconds). We map output PTS:
        pts_out = ∫₀ᵗ (1/speed(τ)) dτ
    For speed = a + b·smooth(τ/T_total):
        Numerical: tabulate at high resolution.

    SIMPLER PATH: use a polynomial fit to (1/speed) and let ffmpeg evaluate
    it per frame. That's what we do below.
    """
    a = s_start
    b = s_end - s_start
    # 1/speed(t) where t = T/duration ∈ [0,1]
    # speed = a + b·(3t² - 2t³)
    # We can't analytically integrate; instead use setpts with a piecewise expr
    # via the if() chain. ffmpeg expressions support if(cond, then, else).

    # Sample N points; at each, integrate trapezoidally to get cumulative output time
    N = 50
    samples = []
    cum_out = 0.0
    prev_inv = 1.0 / s_start
    for i in range(N + 1):
        t = i / N
        smooth = 3 * t * t - 2 * t * t * t
        sp = a + b * smooth
        inv = 1.0 / sp
        if i > 0:
            cum_out += (prev_inv + inv) / 2 * (duration / N)
        samples.append((i * (duration / N), cum_out))
        prev_inv = inv

    # Build a piecewise linear setpts expression as nested if()
    # PTS_out(T) = linear interpolation through (samples[i][0], samples[i][1])
    # ffmpeg setpts syntax: setpts=expr where TS is in seconds (use T)
    # expression: lerp(T, t_lo, t_hi, out_lo, out_hi)
    # For efficiency, generate a single big if-chain or use lookup via floor

    # Simpler: build a piecewise expression that ffmpeg can evaluate
    # Each segment: if(lte(T, t_hi), out_lo + (T - t_lo) * slope, ...)
    expr = f"{samples[-1][1]:.6f}"  # default if past end
    for i in range(N - 1, -1, -1):
        t_lo, out_lo = samples[i]
        t_hi, out_hi = samples[i + 1]
        slope = (out_hi - out_lo) / (t_hi - t_lo) if (t_hi - t_lo) > 0 else 0
        expr = f"if(lte(T,{t_hi:.4f}),{out_lo:.6f}+(T-{t_lo:.4f})*{slope:.6f},{expr})"
    return f"({expr})/TB"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Source video")
    p.add_argument("output", help="Output video")
    p.add_argument("--ss", type=float, default=0.0, help="Source start time (s)")
    p.add_argument("--src-dur", type=float, required=True, help="Source duration consumed (s)")
    p.add_argument("--out-dur", type=float, required=True, help="Output timeline duration (s)")
    p.add_argument("--s-start", type=float, required=True, help="Speed at t=0 in output (1.0=normal, 0.5=slowmo)")
    p.add_argument("--s-end", type=float, required=True, help="Speed at t=out_dur")
    p.add_argument("--fps", type=int, default=30, help="Output framerate")
    p.add_argument("--crf", type=int, default=20, help="x264 CRF")
    args = p.parse_args()

    print(f"⚠ WARNING: bezier ramp can be 2-3× slower than linear at 4K.")
    print(f"   Run this on ONE clip to validate before integrating into a full render.\n")

    expr = build_setpts_expr(args.s_start, args.s_end, args.out_dur)
    fc = f"setpts={expr}"

    out_frames = int(round(args.out_dur * args.fps))
    cmd = [FFMPEG, "-y", "-loglevel", "info",
           "-ss", f"{args.ss:.3f}",
           "-t", f"{args.src_dur:.3f}",
           "-i", args.input,
           "-vf", fc,
           "-frames:v", str(out_frames),
           "-r", str(args.fps),
           "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
           "-pix_fmt", "yuv420p", "-an",
           args.output]

    print(f"🎬 Source: {args.input} (ss={args.ss}s, src_dur={args.src_dur}s)")
    print(f"🎯 Output: {args.output} ({args.out_dur}s, {out_frames} frames @ {args.fps}fps)")
    print(f"🎚 Ramp: speed {args.s_start} → {args.s_end} (cubic ease-in-out)\n")

    import time
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    if r.returncode != 0:
        print(f"❌ {r.stderr[-500:]}")
        sys.exit(1)
    size_mb = Path(args.output).stat().st_size // 1024 // 1024
    print(f"\n✅ {args.output} ({size_mb} MB · {elapsed:.1f}s render)")
    print(f"   Inspect carefully — if you see judder, fall back to constant speed.")


if __name__ == "__main__":
    main()
