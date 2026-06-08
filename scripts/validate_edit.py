#!/usr/bin/env python3
"""validate_edit.py — Catch source-insufficient plans BEFORE you waste 30 min on a render.

For each plan in the EDIT list, checks:
  - source file exists
  - src_start + (out_dur * speed) ≤ source_duration  (else plan will be clamped silently → drift)
  - For ramps (s_start, s_end): worst case (max speed) still fits

Usage:
    python3 validate_edit.py path/to/my_project.py [--clips-dir /path/if/different]

Exit code 0 = OK, 1 = at least one plan would fail
"""
import argparse
import ast
import shutil
import subprocess
import sys
from pathlib import Path

FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"


def extract_edit_list(script_path: Path) -> list:
    """Parse Python script and extract the EDIT = [...] assignment as Python list of tuples."""
    tree = ast.parse(script_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EDIT":
                    # Convert literal AST → Python value (only safe for literals)
                    return ast.literal_eval(node.value)
    return []


def find_clips_dir(script_path: Path, override: str | None) -> Path | None:
    """Look for CLIPS or CLIP_DIR variable in script, or use override."""
    if override:
        return Path(override).expanduser().resolve()
    tree = ast.parse(script_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("CLIPS", "CLIP_DIR", "CLIPS_DIR"):
                    try:
                        return Path(ast.literal_eval(node.value)).expanduser().resolve()
                    except Exception:
                        pass
    return None


def src_duration(path: Path) -> float | None:
    if not path.exists():
        return None
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return None


def required_src(out_dur: float, speed) -> float:
    """How much source duration is consumed? For ramps, use max speed (worst case)."""
    if isinstance(speed, (tuple, list)) and len(speed) == 2:
        # Linear ramp s_start → s_end: avg speed = (s_start + s_end) / 2
        # But to avoid clamping, source consumed = out_dur * avg
        return out_dur * (speed[0] + speed[1]) / 2.0
    return out_dur * float(speed)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("script", help="Path to my_project.py with EDIT = [...]")
    p.add_argument("--clips-dir", help="Override clips directory")
    args = p.parse_args()

    script_path = Path(args.script).expanduser().resolve()
    if not script_path.exists():
        sys.exit(f"❌ Script not found: {script_path}")

    try:
        edit = extract_edit_list(script_path)
    except Exception as e:
        sys.exit(f"❌ Could not parse EDIT list (only literal lists/tuples supported): {e}")

    if not edit:
        sys.exit(f"❌ No EDIT = [...] assignment found in {script_path}")

    clips_dir = find_clips_dir(script_path, args.clips_dir)
    if not clips_dir:
        sys.exit(f"❌ Could not locate CLIPS directory. Pass --clips-dir.")

    print(f"📂 Clips dir: {clips_dir}")
    print(f"📋 EDIT list: {len(edit)} plans\n")

    ok_count = 0
    fail = []
    cum = 0.0
    for i, entry in enumerate(edit, 1):
        # Entry: (fname, src_start, out_dur, speed, sfx, reframe, extra)
        if len(entry) < 4:
            fail.append((i, entry, "tuple too short (need at least 4 fields)"))
            continue
        fname, src_start, out_dur, speed = entry[0], entry[1], entry[2], entry[3]
        src_path = clips_dir / fname
        src_dur = src_duration(src_path)
        if src_dur is None:
            fail.append((i, entry, f"source not found or unprobable: {src_path}"))
            continue

        req = required_src(out_dur, speed)
        end = src_start + req
        ok = end <= src_dur
        margin = src_dur - end

        speed_str = (f"{speed:.2f}" if isinstance(speed, (int, float))
                     else f"{speed[0]:.2f}→{speed[1]:.2f}")
        status = "✅" if ok else "❌"
        print(f"{status} [{i:>2}] {fname[:50]:<50} "
              f"src=[{src_start:>6.3f}→{end:>7.3f} / {src_dur:>7.3f}] "
              f"speed={speed_str:<10} margin={margin:+7.3f}s  cum_out={cum + out_dur:>7.3f}s")
        cum += out_dur
        if ok:
            ok_count += 1
        else:
            fail.append((i, entry, f"needs {end - src_dur:.3f}s more source"))

    print(f"\n{'='*100}\nResult: {ok_count}/{len(edit)} plans OK, {len(fail)} failed")
    print(f"Total output duration: {cum:.3f}s ({cum/60:.2f} min)")

    if fail:
        print(f"\n❌ FAILURES (these will be silently clamped → cumulative drift):")
        for i, entry, reason in fail:
            print(f"  Plan #{i}: {entry[0]}")
            print(f"    → {reason}")
            print(f"    Fix: reduce out_dur, reduce speed, or shift src_start back")
        sys.exit(1)

    print("\n✅ All plans fit within their source duration. Safe to render.")


if __name__ == "__main__":
    main()
