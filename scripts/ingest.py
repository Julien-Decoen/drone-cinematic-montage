#!/usr/bin/env python3
"""ingest.py — DIT (Data Ingest Technician) workflow: backup + proxies + naming + metadata.

Run this RIGHT AFTER coming back from a shoot (before deleting the SD card!).

Does:
  1. Copies all clips from source card/folder to working directory
  2. (Optional) Mirrors to a backup location (3-2-1 rule: 3 copies, 2 supports, 1 offsite)
  3. Generates low-res proxies (240p H.264) for fast editing/review
  4. Renames files using a deterministic pattern (e.g. INT_D1_001.MP4)
  5. Writes metadata.json with each clip's duration, fps, resolution, rating placeholder

Usage:
    python3 ingest.py --source /Volumes/DJI_SD --project myproject --out ~/Documents/drone/MyProject
    python3 ingest.py --source ~/Downloads/raw_clips --project NOR --out ~/Drone/Norway \\
        --backup /Volumes/ExternalSSD/drone_backup --rename-pattern '{project}_D{day}_{num:03d}'
    python3 ingest.py --source ~/clips --project TEST --out ~/test --skip-proxy

After ingest, use `cull.py` to rate and filter the proxies.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
EXTS = {".mp4", ".mov", ".m4v"}


def probe(path: Path) -> dict:
    r = subprocess.run([FFPROBE, "-v", "error",
                        "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,r_frame_rate",
                        "-show_entries", "format=duration,size,creation_time",
                        "-of", "json", str(path)],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        s = d.get("streams", [{}])[0]
        fmt = d.get("format", {})
        fps_str = s.get("r_frame_rate", "0/1").split("/")
        fps = float(fps_str[0]) / float(fps_str[1]) if float(fps_str[1]) else 0.0
        return {
            "width": s.get("width"),
            "height": s.get("height"),
            "fps": round(fps, 2),
            "duration": round(float(fmt.get("duration", 0)), 3),
            "size_mb": round(int(fmt.get("size", 0)) / 1024 / 1024, 1),
            "creation_time": fmt.get("tags", {}).get("creation_time"),
        }
    except Exception as e:
        return {"error": str(e)[:200]}


def gen_proxy(input_path: Path, output_path: Path, height: int = 240):
    """240p H.264 proxy for fast editing/review."""
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-i", str(input_path),
           "-vf", f"scale=-2:{height}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
           "-c:a", "aac", "-b:a", "96k",
           "-movflags", "+faststart",
           str(output_path)]
    subprocess.run(cmd, capture_output=True, text=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", required=True, help="SD card mount or folder with raw clips")
    p.add_argument("--out", required=True, help="Working project folder (will create subdirs)")
    p.add_argument("--project", required=True, help="Short project code (e.g. INT, NOR, ICE)")
    p.add_argument("--backup", help="Optional backup mirror location (3-2-1 rule)")
    p.add_argument("--day", type=int, default=1, help="Shooting day number (default 1)")
    p.add_argument("--rename-pattern", default="{project}_D{day}_{num:03d}",
                   help="Filename pattern. Vars: {project}, {day}, {num}, {orig}")
    p.add_argument("--skip-proxy", action="store_true", help="Don't generate 240p proxies")
    p.add_argument("--proxy-height", type=int, default=240, help="Proxy height in pixels (default 240)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    args = p.parse_args()

    src = Path(args.source).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    backup = Path(args.backup).expanduser().resolve() if args.backup else None

    if not src.is_dir():
        sys.exit(f"❌ Source not found: {src}")

    # Find clips
    clips = sorted([p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in EXTS])
    if not clips:
        sys.exit(f"❌ No clips found in {src}")

    # Setup output structure
    masters_dir = out / "01_masters"
    proxies_dir = out / "02_proxies"
    metadata_path = out / "metadata.json"

    print(f"📁 Source: {src}")
    print(f"📂 Output: {out}")
    print(f"   ├── 01_masters/   ({len(clips)} clips)")
    print(f"   ├── 02_proxies/   ({'skipped' if args.skip_proxy else 'will generate'})")
    print(f"   └── metadata.json")
    if backup:
        print(f"🔒 Backup mirror: {backup}/  (3-2-1 rule)")
    print(f"📛 Naming: {args.rename_pattern}\n")

    if not args.dry_run:
        masters_dir.mkdir(parents=True, exist_ok=True)
        if not args.skip_proxy:
            proxies_dir.mkdir(parents=True, exist_ok=True)
        if backup:
            backup.mkdir(parents=True, exist_ok=True)

    metadata = {
        "project": args.project,
        "ingest_date": datetime.now().isoformat(timespec="seconds"),
        "source": str(src),
        "clips": []
    }

    for i, cp in enumerate(clips, 1):
        new_stem = args.rename_pattern.format(
            project=args.project, day=args.day, num=i, orig=cp.stem)
        new_name = new_stem + cp.suffix
        master_path = masters_dir / new_name
        proxy_path = proxies_dir / f"{new_stem}_proxy.mp4"

        print(f"[{i:>3}/{len(clips)}] {cp.name}  →  {new_name}")

        if args.dry_run:
            continue

        # Copy to master
        if master_path.exists():
            print(f"      ⏭ already in masters")
        else:
            shutil.copy2(cp, master_path)

        # Probe metadata
        info = probe(master_path)
        info["original_name"] = cp.name
        info["new_name"] = new_name
        info["rating"] = None   # filled by cull.py
        info["tags"] = []       # filled by cull.py
        metadata["clips"].append(info)

        # Backup mirror
        if backup:
            backup_path = backup / new_name
            if not backup_path.exists():
                shutil.copy2(cp, backup_path)
                print(f"      ✓ backup → {backup}")

        # Proxy
        if not args.skip_proxy:
            if proxy_path.exists():
                print(f"      ⏭ proxy exists")
            else:
                print(f"      ⏳ generating proxy {args.proxy_height}p...")
                gen_proxy(master_path, proxy_path, args.proxy_height)

    if not args.dry_run:
        metadata_path.write_text(json.dumps(metadata, indent=2))
        print(f"\n✅ Ingest complete.")
        print(f"   Masters: {masters_dir}")
        if not args.skip_proxy:
            print(f"   Proxies: {proxies_dir}")
        print(f"   Metadata: {metadata_path}")
        if backup:
            print(f"   Backup:  {backup}")
        print(f"\n🚀 Next step: cull/rate clips:")
        print(f"   python3 {Path(__file__).parent / 'cull.py'} {proxies_dir if not args.skip_proxy else masters_dir}")
    else:
        print(f"\n[dry-run] Would have copied {len(clips)} clips to {masters_dir}")


if __name__ == "__main__":
    main()
