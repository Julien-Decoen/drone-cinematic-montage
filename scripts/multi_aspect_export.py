#!/usr/bin/env python3
"""multi_aspect_export.py — Generate platform-specific deliverables from a 16:9 master.

From a single 16:9 master (3840×2160 or 1920×1080), produces:
  - 9:16  1080×1920 (Reels / TikTok / YT Shorts)
  - 1:1   1080×1080 (Instagram feed)
  - 4:5   1080×1350 (Instagram portrait)
  - + optional letterboxed 16:9 1080p for Twitter / quick-share

By default uses CENTER CROP. With --blur-bg, fills the borders with blurred
copies of the source (Instagram-style). With --saliency, attempts subject-aware
reframing (TODO: requires opencv + saliency model — currently falls back to center).

Usage:
    python3 multi_aspect_export.py master.mp4                           # all 3 (9:16, 1:1, 4:5) center-crop
    python3 multi_aspect_export.py master.mp4 --aspects 9:16,1:1        # only these two
    python3 multi_aspect_export.py master.mp4 --blur-bg                 # Instagram-style blurred bg
    python3 multi_aspect_export.py master.mp4 --out /path/to/exports/   # custom output dir
    python3 multi_aspect_export.py master.mp4 --duration 60             # trim to first 60s (for shorts)
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

ASPECTS = {
    "9:16":  (1080, 1920),
    "1:1":   (1080, 1080),
    "4:5":   (1080, 1350),
    "16:9":  (1920, 1080),
    "2:3":   (1080, 1620),
}


def probe_res(path: Path):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,duration",
                        "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    parts = r.stdout.strip().split(",")
    return int(parts[0]), int(parts[1]), float(parts[2]) if len(parts) > 2 else None


def export_aspect(input_path: Path, output_path: Path, target_w: int, target_h: int,
                  duration: float | None, blur_bg: bool, saliency: bool):
    src_w, src_h, _ = probe_res(input_path)
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if blur_bg:
        # Source scaled to fit centered (no crop), with blurred-copy background filling the rest
        vf = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},boxblur=30:5[bgb];"
            f"[fg]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2[v]"
        )
        map_arg = ["-filter_complex", vf, "-map", "[v]"]
    else:
        # Center crop (saliency=TODO, falls back to center)
        if saliency:
            print(f"   ℹ saliency mode not yet implemented, using center crop")
        if src_ratio > target_ratio:
            # Source wider → crop width
            crop_w = int(src_h * target_ratio)
            crop_w -= crop_w % 2
            vf = f"crop={crop_w}:{src_h},scale={target_w}:{target_h}"
        else:
            # Source taller → crop height
            crop_h = int(src_w / target_ratio)
            crop_h -= crop_h % 2
            vf = f"crop={src_w}:{crop_h},scale={target_w}:{target_h}"
        map_arg = ["-vf", vf]

    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", str(input_path)]
    if duration:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += map_arg + [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"   ❌ {r.stderr[-300:]}")
        return False
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("master", help="16:9 master video")
    p.add_argument("--aspects", default="9:16,1:1,4:5",
                   help="Comma-separated list of aspects to export (default: 9:16,1:1,4:5)")
    p.add_argument("--out", help="Output directory (default: <master>_multi/)")
    p.add_argument("--duration", type=float, help="Trim to this duration (for shorts)")
    p.add_argument("--blur-bg", action="store_true",
                   help="Use blurred-source background instead of cropping (Instagram-style)")
    p.add_argument("--saliency", action="store_true",
                   help="Use subject-aware reframing (TODO — currently falls back to center)")
    args = p.parse_args()

    master = Path(args.master).expanduser().resolve()
    if not master.exists():
        sys.exit(f"❌ Master not found: {master}")

    out_dir = Path(args.out).expanduser().resolve() if args.out else master.parent / f"{master.stem}_multi"
    out_dir.mkdir(parents=True, exist_ok=True)

    aspects = [a.strip() for a in args.aspects.split(",")]
    src_w, src_h, src_dur = probe_res(master)
    print(f"📂 Master: {master.name} · {src_w}×{src_h} · {src_dur:.1f}s")
    print(f"📂 Output: {out_dir}")
    print(f"🎯 Aspects: {aspects}{' (blurred bg)' if args.blur_bg else ' (center-crop)'}")
    if args.duration:
        print(f"✂  Trim to {args.duration:.1f}s")
    print()

    for asp in aspects:
        if asp not in ASPECTS:
            print(f"   ⚠ unknown aspect '{asp}', skipping (valid: {list(ASPECTS.keys())})")
            continue
        w, h = ASPECTS[asp]
        out_name = f"{master.stem}_{asp.replace(':', 'x')}_{w}x{h}.mp4"
        out_path = out_dir / out_name
        print(f"⏳ {asp} → {w}×{h}  →  {out_name}")
        if export_aspect(master, out_path, w, h, args.duration, args.blur_bg, args.saliency):
            size_mb = out_path.stat().st_size // 1024 // 1024
            print(f"   ✓ {size_mb} MB")

    print(f"\n✅ Done. All deliverables in {out_dir}")


if __name__ == "__main__":
    main()
