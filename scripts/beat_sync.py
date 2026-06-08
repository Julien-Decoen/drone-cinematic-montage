#!/usr/bin/env python3
"""beat_sync.py — Beat-precise music synchronization with librosa.

Cuts that land on a snare hit / downbeat hit 3x harder emotionally than cuts
that land near a peak. This script:
  1. Loads the music track with librosa
  2. Detects all beats + downbeats + onsets
  3. (Optional) Reads an EDIT list from a Python script
  4. For each plan boundary in EDIT, finds the nearest beat
  5. Prints suggested out_dur adjustments to snap each cut on a beat
  6. (--apply) Rewrites the script with snapped values

Usage:
    # 1. Just analyze music — print beats
    python3 beat_sync.py music.mp3

    # 2. Compare EDIT cuts to beats, suggest snaps
    python3 beat_sync.py music.mp3 --script my_project.py

    # 3. Apply snaps (rewrites my_project.py in place — uses .bak backup)
    python3 beat_sync.py music.mp3 --script my_project.py --apply

    # 4. Tighter snapping (only snap if within 0.5s of a beat, default 1.0)
    python3 beat_sync.py music.mp3 --script my_project.py --max-snap 0.5

Requires:  pip install librosa
"""
import argparse
import ast
import shutil
import sys
from pathlib import Path

try:
    import librosa
    import numpy as np
except ImportError:
    sys.exit("❌ Install librosa first: pip install librosa")


def fmt_time(t: float) -> str:
    mm = int(t // 60); ss = t - mm * 60
    return f"{mm}:{ss:06.3f}"


def detect_beats(music_path: Path):
    """Returns (tempo, beat_times, downbeat_times, onset_times)."""
    print(f"⏳ Loading {music_path.name}...")
    y, sr = librosa.load(str(music_path))
    print(f"   duration: {len(y)/sr:.2f}s · sr={sr}Hz")

    print(f"⏳ Detecting beats...")
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    # tempo can be returned as a numpy scalar/array — coerce safely
    tempo_val = float(np.asarray(tempo).flat[0])

    # Approximate downbeats: every 4th beat in 4/4 (heuristic)
    downbeats = beats[::4]

    # Strong onsets (rhythmic accents)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units="time")

    return tempo_val, list(beats), list(downbeats), list(onsets)


def find_nearest(target: float, candidates: list[float], max_delta: float):
    """Return (nearest_value, delta) or (None, None) if no candidate within max_delta."""
    if not candidates:
        return None, None
    arr = np.asarray(candidates)
    idx = int(np.argmin(np.abs(arr - target)))
    delta = arr[idx] - target
    if abs(delta) > max_delta:
        return None, None
    return float(arr[idx]), float(delta)


def extract_edit(script_path: Path):
    tree = ast.parse(script_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "EDIT":
                    return ast.literal_eval(node.value)
    return None


def apply_snaps(script_path: Path, new_durations: list[float]):
    """Rewrite the script with snapped out_durs. Saves .bak first."""
    backup = script_path.with_suffix(script_path.suffix + ".bak")
    shutil.copy(script_path, backup)
    src = script_path.read_text()
    tree = ast.parse(src)

    # Find EDIT assignment node and rewrite each tuple's 3rd element (out_dur)
    new_src_lines = src.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "EDIT":
                    if not isinstance(node.value, ast.List):
                        continue
                    for i, elt in enumerate(node.value.elts):
                        if i >= len(new_durations): break
                        if not isinstance(elt, ast.Tuple) or len(elt.elts) < 3:
                            continue
                        old_node = elt.elts[2]
                        line_idx = old_node.lineno - 1
                        line = new_src_lines[line_idx]
                        # Replace the literal: hacky but works for our format
                        old_val = ast.literal_eval(old_node)
                        new_val = new_durations[i]
                        # Replace first occurrence of old value on the line
                        old_str_options = [f"{old_val:.3f}", f"{old_val:g}", str(old_val)]
                        for old_str in old_str_options:
                            if old_str in line:
                                new_line = line.replace(old_str, f"{new_val:.3f}", 1)
                                new_src_lines[line_idx] = new_line
                                break
    script_path.write_text("\n".join(new_src_lines))
    print(f"\n✅ Snapped script written. Backup at {backup.name}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("music", help="Music track (mp3/wav/m4a)")
    p.add_argument("--script", help="Path to my_project.py with EDIT = [...]")
    p.add_argument("--apply", action="store_true",
                   help="Apply snaps to script (rewrites in place, backup saved as .bak)")
    p.add_argument("--max-snap", type=float, default=1.0,
                   help="Max distance (s) to snap to a beat (default 1.0)")
    p.add_argument("--use", choices=["beats", "downbeats", "onsets"], default="beats",
                   help="Snap target type (default: beats)")
    args = p.parse_args()

    music_path = Path(args.music).expanduser().resolve()
    if not music_path.exists():
        sys.exit(f"❌ Music not found: {music_path}")

    tempo, beats, downbeats, onsets = detect_beats(music_path)
    print(f"\n🎵 Tempo: {tempo:.1f} BPM")
    print(f"🎵 Beats:      {len(beats)} · first 5: {[f'{b:.2f}' for b in beats[:5]]}")
    print(f"🎵 Downbeats:  {len(downbeats)} (heuristic every 4th beat)")
    print(f"🎵 Onsets:     {len(onsets)} · strong rhythmic accents")

    snap_set = {"beats": beats, "downbeats": downbeats, "onsets": onsets}[args.use]

    if not args.script:
        print(f"\n💡 No --script provided. Re-run with --script my_project.py to compare cuts.")
        return

    script_path = Path(args.script).expanduser().resolve()
    edit = extract_edit(script_path)
    if not edit:
        sys.exit(f"❌ No EDIT = [...] found in {script_path}")

    print(f"\n{'='*100}")
    print(f"📋 Snap audit — comparing each cut to nearest {args.use} (max delta ±{args.max_snap}s)")
    print(f"{'='*100}")
    print(f"{'#':<4} {'fname':<45} {'cut_now':>10} {'nearest':>10} {'delta':>9} {'new_dur':>10}")
    print("-" * 100)

    cum = 0.0
    new_durations = []
    snapped = 0
    for i, entry in enumerate(edit, 1):
        fname = entry[0]
        out_dur = entry[2]
        cut_at = cum + out_dur
        nearest, delta = find_nearest(cut_at, snap_set, args.max_snap)
        if nearest is not None and abs(delta) > 0.02:  # don't bother for <20ms
            new_out_dur = out_dur + delta
            mark = "🔄"
            snapped += 1
        else:
            new_out_dur = out_dur
            mark = "✓" if nearest else "—"
            delta = delta or 0.0
        print(f"{i:<4} {fname[:45]:<45} {fmt_time(cut_at):>10} "
              f"{fmt_time(nearest) if nearest else '—':>10} {delta:+8.3f}s {new_out_dur:>9.3f}s {mark}")
        new_durations.append(new_out_dur)
        cum += new_out_dur

    print(f"\n📊 {snapped}/{len(edit)} cuts would be snapped (delta > 20ms)")

    if args.apply:
        apply_snaps(script_path, new_durations)
    else:
        print(f"\n💡 Run with --apply to rewrite the script (creates a .bak backup)")


if __name__ == "__main__":
    main()
