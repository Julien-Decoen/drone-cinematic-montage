#!/usr/bin/env python3
"""master_audio_lufs.py — LUFS audio mastering (2-pass loudnorm).

Normalizes audio to a streaming platform's target loudness:
  - YouTube  : -14 LUFS (default)
  - Spotify  : -14 LUFS
  - Apple    : -16 LUFS
  - Broadcast: -23 LUFS (EBU R128)

Without this step, your master sounds either crushed (YouTube turns it down)
or quiet (vs other content) on streaming platforms.

Usage:
    python3 master_audio_lufs.py master.mp4                       # → master_lufs.mp4 (-14 LUFS, YouTube)
    python3 master_audio_lufs.py master.mp4 --target -16          # Apple
    python3 master_audio_lufs.py master.mp4 -o output.mp4         # custom output path
    python3 master_audio_lufs.py master.mp4 --audio-only out.mp3  # just normalize an audio file
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def measure_loudness(input_path: str, target_lufs: float = -14.0) -> dict:
    """Pass 1: measure current loudness. Returns dict with input_i, input_lra, input_tp, input_thresh, target_offset."""
    print(f"⏳ Pass 1/2: measuring loudness of {os.path.basename(input_path)}...")
    cmd = [FFMPEG, "-i", input_path,
           "-af", f"loudnorm=I={target_lufs}:LRA=11:TP=-1.5:print_format=json",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    # loudnorm prints JSON to stderr at the end
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.DOTALL)
    if not m:
        sys.exit(f"❌ Could not parse loudnorm output. ffmpeg stderr tail:\n{r.stderr[-500:]}")
    data = json.loads(m.group(0))
    print(f"   ✓ measured: input_i={data['input_i']} LUFS, "
          f"input_tp={data['input_tp']} dBTP, "
          f"input_lra={data['input_lra']} LU")
    return data


def apply_loudnorm(input_path: str, output_path: str, target_lufs: float,
                   measured: dict, copy_video: bool = True):
    """Pass 2: apply loudnorm with measured parameters (linear normalization)."""
    print(f"⏳ Pass 2/2: applying normalization to {target_lufs} LUFS...")
    af = (f"loudnorm=I={target_lufs}:LRA=11:TP=-1.5:"
          f"measured_I={measured['input_i']}:"
          f"measured_LRA={measured['input_lra']}:"
          f"measured_TP={measured['input_tp']}:"
          f"measured_thresh={measured['input_thresh']}:"
          f"offset={measured['target_offset']}:"
          f"linear=true:print_format=summary")
    cmd = [FFMPEG, "-y", "-i", input_path]
    if copy_video:
        cmd += ["-map", "0:v", "-map", "0:a", "-c:v", "copy"]
    cmd += ["-af", af, "-c:a", "aac", "-b:a", "320k", output_path]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"❌ Pass 2 failed:\n{r.stderr[-500:]}")
    # Parse summary
    m = re.search(r"Output Integrated:\s*(-?[\d.]+) LUFS", r.stderr)
    if m:
        print(f"   ✓ output: {m.group(1)} LUFS (target {target_lufs})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Input video or audio file")
    p.add_argument("-o", "--output", help="Output path (default: <input>_lufs<ext>)")
    p.add_argument("--target", type=float, default=-14.0,
                   help="Target integrated loudness in LUFS (default -14 = YouTube/Spotify)")
    p.add_argument("--audio-only", action="store_true",
                   help="Treat input as audio-only (no video stream)")
    args = p.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        sys.exit(f"❌ Not found: {input_path}")

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        output_path = input_path.parent / f"{input_path.stem}_lufs{input_path.suffix}"

    print(f"📂 Input:  {input_path}")
    print(f"📂 Output: {output_path}")
    print(f"🎯 Target: {args.target} LUFS\n")

    measured = measure_loudness(str(input_path), args.target)
    apply_loudnorm(str(input_path), str(output_path), args.target, measured,
                   copy_video=not args.audio_only)

    print(f"\n✅ {output_path} ({os.path.getsize(output_path)//1024//1024} MB)")
    print(f"   Now uploadable to YouTube/Spotify without auto-normalization penalty.")


if __name__ == "__main__":
    main()
