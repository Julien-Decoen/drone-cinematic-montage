#!/usr/bin/env python3
"""stabilize.py — Post-stabilization via ffmpeg vidstab (2-pass).

The DJI gimbal is good but not perfect. Pros run an extra software stab pass
to eliminate micro-jitter. ffmpeg has vidstab built-in (since ~4.0).

This script:
  - Takes a folder of clips OR a single clip
  - Runs vidstabdetect (pass 1) + vidstabtransform (pass 2)
  - Outputs to <input_dir>/stabilized/ (or specified --out)
  - Skips files already stabilized

Usage:
    python3 stabilize.py /path/to/clips                       # whole folder → ./stabilized/
    python3 stabilize.py /path/to/clip.mp4                    # single clip → ./clip_stab.mp4
    python3 stabilize.py /path/to/clips -o /path/to/output    # custom output dir
    python3 stabilize.py /path/to/clips --smoothing 30        # higher = smoother (10-100, default 30)
    python3 stabilize.py /path/to/clips --shakiness 5         # how shaky source is (1-10, default 5)
    python3 stabilize.py /path/to/clips --crop                # crop to remove edge artifacts (default: keep black borders)
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
EXTS = {".mp4", ".mov", ".m4v", ".MP4", ".MOV"}


def detect_stabilizer() -> str:
    """Returns 'vidstab' (preferred, 2-pass), 'deshake' (fallback, 1-pass), or 'none'."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-filters"], capture_output=True, text=True)
    if "vidstabdetect" in r.stdout and "vidstabtransform" in r.stdout:
        return "vidstab"
    if "deshake" in r.stdout:
        return "deshake"
    return "none"


def stabilize_vidstab(input_path: Path, output_path: Path, shakiness: int,
                     smoothing: int, crop_edges: bool) -> bool:
    """2-pass vidstab (preferred — best quality)."""
    trf_file = output_path.parent / f".{input_path.stem}.trf"

    # Pass 1
    detect = [FFMPEG, "-y", "-loglevel", "error", "-i", str(input_path),
              "-vf", f"vidstabdetect=shakiness={shakiness}:accuracy=15:result={trf_file}",
              "-f", "null", "-"]
    if subprocess.run(detect, capture_output=True, text=True).returncode != 0:
        return False

    # Pass 2
    crop_param = "crop=keep" if not crop_edges else "crop=black"
    transform = [FFMPEG, "-y", "-loglevel", "error", "-i", str(input_path),
                 "-vf", f"vidstabtransform=input={trf_file}:smoothing={smoothing}:{crop_param},"
                        f"unsharp=5:5:0.8:3:3:0.4",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-c:a", "copy", str(output_path)]
    r = subprocess.run(transform, capture_output=True, text=True)
    try: trf_file.unlink()
    except: pass
    return r.returncode == 0


def stabilize_deshake(input_path: Path, output_path: Path, crop_edges: bool) -> bool:
    """1-pass deshake (fallback when vidstab not compiled in)."""
    edge = 0 if crop_edges else 1  # 0=mirror+blank, 1=original
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", str(input_path),
           "-vf", f"deshake=edge={edge}:rx=32:ry=32:blocksize=10:contrast=125",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-c:a", "copy", str(output_path)]
    return subprocess.run(cmd, capture_output=True, text=True).returncode == 0


def stabilize_clip(input_path: Path, output_path: Path, shakiness: int,
                   smoothing: int, crop_edges: bool, backend: str) -> bool:
    if backend == "vidstab":
        return stabilize_vidstab(input_path, output_path, shakiness, smoothing, crop_edges)
    elif backend == "deshake":
        return stabilize_deshake(input_path, output_path, crop_edges)
    return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Folder of clips OR a single clip")
    p.add_argument("-o", "--out", help="Output folder (default: <input>/stabilized/ or <input>_stab.mp4)")
    p.add_argument("--shakiness", type=int, default=5, choices=range(1, 11),
                   help="How shaky the source is (1-10, default 5)")
    p.add_argument("--smoothing", type=int, default=30,
                   help="Frames smoothing radius (higher = smoother, default 30)")
    p.add_argument("--crop", action="store_true",
                   help="Crop edges instead of black bars (slightly zooms in)")
    p.add_argument("--force", action="store_true",
                   help="Re-stabilize files that already have a stabilized counterpart")
    args = p.parse_args()

    backend = detect_stabilizer()
    if backend == "none":
        sys.exit(f"❌ No stabilizer found in ffmpeg. Need vidstabdetect/transform OR deshake.")
    if backend == "deshake":
        print(f"ℹ Using built-in `deshake` (1-pass). For better quality, install ffmpeg with vidstab:")
        print(f"   brew uninstall ffmpeg && brew install ffmpeg --with-libvidstab")
        print(f"   (or use a conda-forge ffmpeg build which includes vidstab)\n")
    else:
        print(f"✓ Using vidstab (2-pass, recommended)\n")

    input_path = Path(args.input).expanduser().resolve()

    if input_path.is_file():
        # Single clip
        out_path = Path(args.out).expanduser().resolve() if args.out else input_path.parent / f"{input_path.stem}_stab{input_path.suffix}"
        if out_path.exists() and not args.force:
            print(f"  → exists (use --force): {out_path}")
            return
        print(f"⏳ Stabilizing {input_path.name}...")
        if stabilize_clip(input_path, out_path, args.shakiness, args.smoothing, args.crop, backend):
            print(f"✅ {out_path}")
    elif input_path.is_dir():
        out_dir = Path(args.out).expanduser().resolve() if args.out else input_path / "stabilized"
        out_dir.mkdir(parents=True, exist_ok=True)
        clips = sorted([p for p in input_path.iterdir() if p.is_file() and p.suffix in EXTS])
        if not clips:
            sys.exit(f"❌ No clips found in {input_path}")
        print(f"📂 {len(clips)} clips → {out_dir}\n")
        ok = 0
        for i, cp in enumerate(clips, 1):
            out_path = out_dir / cp.name
            if out_path.exists() and not args.force:
                print(f"  [{i}/{len(clips)}] {cp.name}  →  already stabilized (skip)")
                ok += 1
                continue
            print(f"  [{i}/{len(clips)}] stabilizing {cp.name}...")
            if stabilize_clip(cp, out_path, args.shakiness, args.smoothing, args.crop):
                ok += 1
                print(f"     ✓ {out_path.name}")
        print(f"\n✅ {ok}/{len(clips)} clips stabilized → {out_dir}")
        print(f"   Use this folder as CLIPS in your render template instead of the original.")
    else:
        sys.exit(f"❌ Not a file or directory: {input_path}")


if __name__ == "__main__":
    main()
