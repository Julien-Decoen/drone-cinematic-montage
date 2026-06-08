#!/usr/bin/env python3
"""lcut_jcut.py — Build a per-plan audio mix with L-cuts and J-cuts.

Hard audio cuts at every visual cut make the montage feel "haché". Pros use:
  - L-cut: audio from plan A continues 0.3-0.8s INTO plan B
           (the sound 'pulls' the new visual)
  - J-cut: audio from plan B starts 0.3-0.8s BEFORE the visual cut
           (the sound 'announces' the new image)

This script reads an EDIT list + a per-plan SFX mapping (or the existing
audio mix script) and produces a `_lcut_jcut_mix.mp3` where each SFX
EXTENDS or PRECEDES its plan boundary by the requested overlap.

Usage:
    python3 lcut_jcut.py my_project.py
    python3 lcut_jcut.py my_project.py --overlap 0.6 --mode L      # L-cuts only, 0.6s
    python3 lcut_jcut.py my_project.py --mode mixed                # L on even cuts, J on odd

Then in your final mux, use the produced _lcut_jcut_mix.mp3 INSTEAD OF the
default audio mix. The video stays as-is; only audio changes.
"""
import argparse
import ast
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def extract_edit(script: Path):
    tree = ast.parse(script.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "EDIT":
                    return ast.literal_eval(node.value)
    return None


def find_music_path(script: Path):
    tree = ast.parse(script.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "MUSIC":
                    try: return Path(ast.literal_eval(node.value))
                    except: pass
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("script", help="Path to my_project.py")
    p.add_argument("--overlap", type=float, default=0.5,
                   help="Overlap duration in seconds (default 0.5)")
    p.add_argument("--mode", choices=["L", "J", "mixed"], default="mixed",
                   help="L = audio extends past cut, J = audio precedes cut, mixed = alternate")
    p.add_argument("--sfx-dir", help="Folder with real SFX (.mp3) named by plan SFX key, e.g. ambient.mp3")
    p.add_argument("--out", help="Output mix path (default: <script_dir>/_lcut_jcut_mix.mp3)")
    args = p.parse_args()

    script = Path(args.script).expanduser().resolve()
    edit = extract_edit(script)
    if not edit:
        sys.exit(f"❌ No EDIT list in {script}")

    music = find_music_path(script)
    if not music or not music.exists():
        sys.exit(f"❌ Could not find MUSIC path in {script}")

    sfx_dir = Path(args.sfx_dir).expanduser().resolve() if args.sfx_dir else None
    out_path = Path(args.out).expanduser().resolve() if args.out else script.parent / "_lcut_jcut_mix.mp3"

    print(f"📋 EDIT: {len(edit)} plans")
    print(f"🎵 Music: {music.name}")
    print(f"🎚 Overlap: {args.overlap}s · Mode: {args.mode}")
    print()

    # Compute timeline
    cum = 0.0
    boundaries = []  # (plan_idx, start, end, sfx)
    for i, e in enumerate(edit):
        sfx = e[4] if len(e) > 4 else None
        boundaries.append((i, cum, cum + e[2], sfx))
        cum += e[2]
    total = cum

    # Build filter chain: music + per-plan SFX with adjusted start/end
    inputs = ["-i", str(music)]
    filt = [f"[0:a]volume=0.85[mus]"]
    labs = ["[mus]"]
    n = 1
    for i, start, end, sfx in boundaries:
        if not sfx or sfx_dir is None:
            continue
        sfx_path = sfx_dir / f"{sfx}.mp3"
        if not sfx_path.exists():
            print(f"  ⚠ plan {i+1}: no SFX file {sfx_path.name}")
            continue

        # L-cut: extend SFX past plan end into next plan
        # J-cut: start SFX before plan start
        if args.mode == "L":
            sfx_start = start
            sfx_end = min(end + args.overlap, total)
        elif args.mode == "J":
            sfx_start = max(0, start - args.overlap)
            sfx_end = end
        else:  # mixed
            if i % 2 == 0:
                sfx_start = start
                sfx_end = min(end + args.overlap, total)
            else:
                sfx_start = max(0, start - args.overlap)
                sfx_end = end

        dur = sfx_end - sfx_start
        delay_ms = int(sfx_start * 1000)
        fin = min(0.25, dur * 0.1)
        fout = min(0.6, dur * 0.2)

        inputs += ["-stream_loop", "-1", "-i", str(sfx_path)]
        filt.append(
            f"[{n}:a]atrim=duration={dur:.3f},"
            f"afade=t=in:st=0:d={fin:.2f},"
            f"afade=t=out:st={dur-fout:.2f}:d={fout:.2f},"
            f"volume=-15dB,"
            f"adelay={delay_ms}|{delay_ms}[s{i}]"
        )
        labs.append(f"[s{i}]")
        n += 1

    if n == 1:
        print(f"⚠ No SFX files found. Use --sfx-dir to point at real SFX MP3s.")
        print(f"   The script still outputs a music-only file.")

    filt.append(f"{''.join(labs)}amix=inputs={len(labs)}:duration=longest:normalize=0[out]")

    cmd = [FFMPEG, "-y", "-loglevel", "error"] + inputs + [
        "-filter_complex", ";".join(filt),
        "-map", "[out]",
        "-c:a", "libmp3lame", "-q:a", "2",
        "-t", f"{total:.3f}",
        str(out_path)
    ]
    print(f"⏳ Building mix...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"❌ {r.stderr[-400:]}")
    size_kb = out_path.stat().st_size // 1024
    print(f"\n✅ {out_path} ({size_kb} KB · {total:.1f}s)")
    print(f"   Use this MP3 in your final mux instead of the default audio mix.")


if __name__ == "__main__":
    main()
