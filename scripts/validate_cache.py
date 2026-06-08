#!/usr/bin/env python3
"""validate_cache.py — Detect & purge cached sub-clips at wrong resolution.

THE V25.17 BUG: when you switch QUALITY=preview → QUALITY=final, the script
silently reuses the 640×360 clip_NN_*.mp4 from the previous preview pass
because they're named the same. Your final "4K" master is then a 4K letterboxed
640×360 garbage.

This script:
  1. Reads target resolution from script (QUALITY env or QUALITY var)
  2. Probes every clip_NN_*.mp4 in the cache folder
  3. Deletes any cached file whose resolution doesn't match the target
  4. Also wipes main_video.mp4, full_video.mp4, assembly_*.txt (they reference stale clips)

Usage:
    python3 validate_cache.py /tmp/myproject [--quality final]
    python3 validate_cache.py myproject_name           # uses /tmp/<name>
    python3 validate_cache.py path/to/my_project.py    # parses script to find TMP
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

EXPECTED_RES = {
    "preview": (640, 360),
    "final":   (3840, 2160),
}


def resolve_tmp(arg: str) -> Path:
    """Accept: /tmp/xxx, xxx (becomes /tmp/xxx), or path to .py script (parses TMP var)."""
    p = Path(arg).expanduser()
    if p.is_dir():
        return p
    if p.suffix == ".py" and p.exists():
        # Parse script for TMP = "..."
        text = p.read_text()
        m = re.search(r'TMP\s*=\s*[fr]?["\'](.*?)["\']', text)
        if m:
            return Path(m.group(1))
    # Fallback: treat as project name → /tmp/<name>
    candidate = Path("/tmp") / arg
    if candidate.is_dir():
        return candidate
    sys.exit(f"❌ Could not find cache dir for '{arg}' (tried {p}, {candidate})")


def probe_res(path: Path) -> tuple[int, int] | None:
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        w, h = map(int, r.stdout.strip().split(","))
        return (w, h)
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cache_or_script", help="Path to cache dir, project name, or my_project.py")
    p.add_argument("--quality", choices=["preview", "final"], default=None,
                   help="Target quality (default: read from QUALITY env or assume final)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = p.parse_args()

    tmp = resolve_tmp(args.cache_or_script).resolve()
    quality = args.quality or os.environ.get("QUALITY", "final")
    target_w, target_h = EXPECTED_RES[quality]

    print(f"📂 Cache: {tmp}")
    print(f"🎯 Target quality: {quality}  →  {target_w}×{target_h}\n")

    if not tmp.is_dir():
        sys.exit(f"❌ Not a directory: {tmp}")

    # Check all clip_*.mp4
    clip_files = sorted(tmp.glob("clip_*.mp4"))
    bad = []
    for cf in clip_files:
        res = probe_res(cf)
        if res is None:
            print(f"  ⚠ Unreadable: {cf.name}")
            continue
        if res != (target_w, target_h):
            bad.append((cf, res))
            print(f"  ❌ {cf.name}: {res[0]}×{res[1]} (expected {target_w}×{target_h})")
        else:
            print(f"  ✅ {cf.name}: {res[0]}×{res[1]}")

    # Concat/assembly files reference clips by index — wipe if any clip is bad
    concat_files = (list(tmp.glob("main_video.mp4")) + list(tmp.glob("full_video.mp4"))
                    + list(tmp.glob("assembly_*.txt")) + list(tmp.glob("trans_*.mp4")))

    print(f"\n{'='*70}")
    if not bad:
        print(f"✅ All {len(clip_files)} cached clips are at target resolution. Nothing to purge.")
        return

    print(f"⚠ {len(bad)} clips at wrong resolution + {len(concat_files)} dependent files")

    to_delete = [cf for cf, _ in bad] + concat_files
    if args.dry_run:
        print(f"\n[dry-run] Would delete {len(to_delete)} files:")
        for f in to_delete:
            print(f"  - {f}")
        return

    print(f"\n🗑  Deleting {len(to_delete)} files...")
    for f in to_delete:
        try:
            f.unlink()
            print(f"  removed {f.name}")
        except Exception as e:
            print(f"  ⚠ {f.name}: {e}")

    print(f"\n✅ Cache cleaned. Re-launch your render — it will rebuild from scratch at {target_w}×{target_h}.")


if __name__ == "__main__":
    main()
