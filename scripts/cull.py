#!/usr/bin/env python3
"""cull.py — Interactive 1-5 star rating workflow for proxies.

After ingest, you have N clips (often 100-300 on a multi-day shoot).
Goal: narrow down to 20-30 hero clips that will appear in the final edit.

Workflow:
  1. Cull pass: rate each clip 1-5★ (1=skip, 5=hero)
  2. Filter: show only ≥4★ clips → "select reel"
  3. Final cut: from select reel, pick the 20-30 that make the timeline

This script does pass 1 + pass 2.

For each clip, it:
  - Opens it in your default video player (QuickTime on macOS)
  - Waits for you to watch + press a key 0-5
  - Saves the rating to ratings.json (and updates metadata.json if present)
  - Repeats

You can quit anytime with 'q' — progress is saved after each rating.

Usage:
    python3 cull.py /path/to/proxies                       # interactive rating loop
    python3 cull.py /path/to/proxies --filter 4            # list clips ≥4★
    python3 cull.py /path/to/proxies --filter 4 --copy /path/to/selects/   # copy selects to folder
    python3 cull.py /path/to/proxies --stats               # show distribution
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXTS = {".mp4", ".mov", ".m4v"}


def load_ratings(ratings_path: Path) -> dict:
    if ratings_path.exists():
        return json.loads(ratings_path.read_text())
    return {}


def save_ratings(ratings_path: Path, ratings: dict):
    ratings_path.write_text(json.dumps(ratings, indent=2, sort_keys=True))


def open_clip(path: Path):
    """Open with default app (macOS: QuickTime / IINA / VLC)."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif sys.platform == "win32":
        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])


def cull_loop(clips_dir: Path):
    ratings_path = clips_dir / "ratings.json"
    ratings = load_ratings(ratings_path)
    clips = sorted([p for p in clips_dir.iterdir() if p.is_file() and p.suffix.lower() in EXTS])
    if not clips:
        sys.exit(f"❌ No clips in {clips_dir}")

    todo = [c for c in clips if c.name not in ratings]
    print(f"📂 {len(clips)} clips · already rated: {len(clips) - len(todo)} · remaining: {len(todo)}\n")

    if not todo:
        print(f"✅ All clips already rated. Use --filter or --stats to see results.")
        return

    print(f"⌨  Controls:  0-5 = rate · n = next (skip without rating) · q = quit\n")

    for i, clip in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {clip.name}", end=" ")
        open_clip(clip)
        try:
            ans = input("→ rating (0-5/n/q): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  saved & quit")
            break
        if ans == "q":
            print("  saved & quit")
            break
        if ans == "n" or ans == "":
            print("  skipped")
            continue
        try:
            rating = int(ans)
            if not (0 <= rating <= 5):
                raise ValueError
            ratings[clip.name] = rating
            save_ratings(ratings_path, ratings)
            stars = "★" * rating + "·" * (5 - rating)
            print(f"  saved: {stars}")
        except ValueError:
            print(f"  invalid input '{ans}' — skipped")

    # Final stats
    print_stats(ratings_path, clips_dir)


def print_stats(ratings_path: Path, clips_dir: Path):
    ratings = load_ratings(ratings_path)
    dist = {i: 0 for i in range(6)}
    for v in ratings.values():
        dist[v] = dist.get(v, 0) + 1
    total = sum(dist.values())
    print(f"\n📊 Rating distribution ({total} rated):")
    for r in [5, 4, 3, 2, 1, 0]:
        bar = "█" * dist[r]
        print(f"   {'★' * r}{'·' * (5-r)}  ({dist[r]:>3}) {bar}")


def filter_selects(clips_dir: Path, min_rating: int, copy_to: Path | None):
    ratings_path = clips_dir / "ratings.json"
    ratings = load_ratings(ratings_path)
    selects = sorted([name for name, r in ratings.items() if r >= min_rating])
    print(f"📋 {len(selects)} selects (≥{min_rating}★):")
    for name in selects:
        rating = ratings[name]
        stars = "★" * rating + "·" * (5 - rating)
        print(f"   {stars}  {name}")
    if copy_to:
        copy_to = copy_to.expanduser().resolve()
        copy_to.mkdir(parents=True, exist_ok=True)
        copied = 0
        for name in selects:
            src = clips_dir / name
            dst = copy_to / name
            if not dst.exists():
                shutil.copy2(src, dst)
                copied += 1
        print(f"\n✅ Copied {copied} new selects to {copy_to}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("clips_dir", help="Folder with proxies (or masters) to rate")
    p.add_argument("--filter", type=int, metavar="MIN", help="List clips with rating ≥ MIN")
    p.add_argument("--copy", type=Path, help="Copy filtered selects to this folder")
    p.add_argument("--stats", action="store_true", help="Show rating distribution and exit")
    args = p.parse_args()

    clips_dir = Path(args.clips_dir).expanduser().resolve()
    if not clips_dir.is_dir():
        sys.exit(f"❌ Not a directory: {clips_dir}")

    if args.stats:
        print_stats(clips_dir / "ratings.json", clips_dir)
    elif args.filter is not None:
        filter_selects(clips_dir, args.filter, args.copy)
    else:
        cull_loop(clips_dir)


if __name__ == "__main__":
    main()
