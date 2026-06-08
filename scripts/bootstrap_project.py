#!/usr/bin/env python3
"""bootstrap_project.py — One-shot project starter for drone-cinematic-montage.

Usage:
    python3 bootstrap_project.py --clips /path/to/clips --music /path/to/music.mp3 \\
        --out ~/my_project --title "INTERLAKEN" --subtitle "Switzerland From Above"

What it does:
  1. ffprobe all clips (duration, fps, D-Log detection via luma)
  2. Detect music duration + estimate emotional peaks (RMS analysis, no librosa req)
  3. Generate <out>/my_project.py pre-filled (from render_template.py)
  4. Generate <out>/build_mix.py (from audio_mix_template.py if present)
  5. Print a starter EDIT list (one entry per clip, default speed/duration)
  6. Print suggested ACT_TRANSITIONS based on music peaks

This eliminates ~6h of manual setup at the start of every new project.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
FFMPEG  = shutil.which("ffmpeg")  or "/opt/homebrew/bin/ffmpeg"
SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_ROOT / "templates" / "render_template.py"
MIX_TEMPLATE = SKILL_ROOT / "templates" / "audio_mix_template.py"


def probe_clip(path: Path) -> dict:
    """Returns dict with duration, fps, width, height, luma_mean (for D-Log detection)."""
    r = subprocess.run(
        [FFPROBE, "-v", "error",
         "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,duration",
         "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:200]}
    data = json.loads(r.stdout)
    s = data.get("streams", [{}])[0]
    fmt = data.get("format", {})

    # fps: rational like "30000/1001" → float
    fps_str = s.get("r_frame_rate", "0/1")
    num, den = fps_str.split("/")
    fps = float(num) / float(den) if float(den) else 0.0

    duration = float(s.get("duration") or fmt.get("duration") or 0)

    # Detect D-Log heuristically: sample mid-clip luma + saturation
    # D-Log has flat low contrast → luma centered ~115, low saturation
    luma_mean, sat_mean = 128.0, 50.0
    try:
        mid = duration / 2.0
        r2 = subprocess.run(
            [FFMPEG, "-ss", f"{mid:.2f}", "-t", "0.5", "-i", str(path),
             "-vf", "scale=320:-1,signalstats,metadata=print",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=15)
        y = re.findall(r"YAVG=([\d.]+)", r2.stderr)
        sat = re.findall(r"SATAVG=([\d.]+)", r2.stderr)
        if y: luma_mean = sum(float(x) for x in y) / len(y)
        if sat: sat_mean = sum(float(x) for x in sat) / len(sat)
    except Exception:
        pass

    return {
        "name": path.name,
        "duration": round(duration, 3),
        "fps": round(fps, 2),
        "width": s.get("width"),
        "height": s.get("height"),
        "luma": round(luma_mean, 1),
        "sat": round(sat_mean, 1),
        # D-Log heuristic: flat luma 105-130 + low SAT (<70) → likely D-Log
        "dlog": (105 <= luma_mean <= 130) and (sat_mean < 70),
    }


def music_peaks(path: Path, n: int = 5) -> dict:
    """Detect approximate music peaks via RMS analysis (no librosa needed).
    Returns duration + list of N peak timestamps."""
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    duration = float(r.stdout.strip() or 0)

    # Sample RMS levels at 0.5s intervals using astats
    r2 = subprocess.run(
        [FFMPEG, "-i", str(path),
         "-af", "astats=metadata=1:reset=0.5,ametadata=print:key=lavfi.astats.Overall.RMS_level",
         "-f", "null", "-"],
        capture_output=True, text=True)

    # Parse pts_time + RMS_level pairs
    times, rms = [], []
    for m in re.finditer(r"pts_time:([\d.]+)\s+lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+|-inf)",
                         r2.stderr):
        t = float(m.group(1))
        v = m.group(2)
        if v == "-inf":
            continue
        times.append(t)
        rms.append(float(v))

    if not times:
        return {"duration": duration, "peaks": [], "note": "RMS extraction failed"}

    # Find local maxima — simple windowed approach
    peaks = []
    window = max(3, len(rms) // 20)  # ~5% window
    for i in range(window, len(rms) - window):
        if rms[i] == max(rms[i - window: i + window + 1]):
            peaks.append((times[i], rms[i]))

    # Sort by amplitude, take top N, sort by time
    peaks.sort(key=lambda x: -x[1])
    peaks = sorted(peaks[:n], key=lambda x: x[0])

    return {
        "duration": round(duration, 3),
        "peaks": [round(t, 2) for t, _ in peaks],
        "peak_levels": [round(r, 1) for _, r in peaks],
    }


def write_my_project(out_dir: Path, clips: list, music: dict, music_path: Path,
                     title: str, subtitle: str):
    """Write a customized my_project.py from the render_template."""
    if not TEMPLATE.exists():
        # Fallback: write a minimal scaffold
        scaffold = MINIMAL_SCAFFOLD
    else:
        scaffold = TEMPLATE.read_text()

    # Inject project-specific values via simple string replacement on KNOWN markers
    clips_dir = clips[0]["__path"].parent if clips else Path(".")
    edit_block = build_edit_block(clips)
    acts = music.get("peaks", [])
    acts_str = ", ".join(f"{p:.2f}" for p in acts) or "# add music peaks here"

    replacements = {
        "@@CLIPS_DIR@@": str(clips_dir),
        "@@MUSIC_PATH@@": str(music_path),
        "@@TITLE@@": title,
        "@@SUBTITLE@@": subtitle,
        "@@EDIT_LIST@@": edit_block,
        "@@ACT_TRANSITIONS@@": acts_str,
        "@@PROJECT_NAME@@": out_dir.name,
        "@@TMP_DIR@@": f"/tmp/{out_dir.name}",
    }
    for k, v in replacements.items():
        scaffold = scaffold.replace(k, v)

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "my_project.py"
    target.write_text(scaffold)
    target.chmod(0o755)
    return target


def build_edit_block(clips: list) -> str:
    """Build a starter EDIT list with one entry per clip, sensible defaults."""
    lines = []
    for c in clips:
        # Default: src_start=0, dur=min(4.0, clip_dur), speed=1.0
        dur = min(4.0, c.get("duration", 4.0))
        sfx = "ambient"
        reframe = "(1.0, 1.05)"
        comment = f"  # luma={c.get('luma'):.0f} sat={c.get('sat'):.0f}" + (" D-LOG" if c.get("dlog") else "")
        lines.append(
            f'    ("{c["name"]}", 0.0, {dur:.3f}, 1.0, "{sfx}", {reframe}, None),{comment}'
        )
    return "\n".join(lines)


def write_mix_script(out_dir: Path, music_path: Path, edit_count: int):
    """Write a starter build_mix.py from the mix template (if exists)."""
    if not MIX_TEMPLATE.exists():
        return None
    content = MIX_TEMPLATE.read_text()
    content = content.replace("@@MUSIC_PATH@@", str(music_path))
    content = content.replace("@@PROJECT_NAME@@", out_dir.name)
    target = out_dir / "build_mix.py"
    target.write_text(content)
    target.chmod(0o755)
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--clips", required=True, help="Folder containing drone MP4 clips")
    p.add_argument("--music", required=True, help="Music track (mp3/wav/m4a)")
    p.add_argument("--out", required=True, help="Output project folder")
    p.add_argument("--title", default="MY MONTAGE", help="Video title overlay")
    p.add_argument("--subtitle", default="From Above", help="Video subtitle overlay")
    p.add_argument("--ext", default="MP4,mp4,MOV,mov", help="Clip file extensions (comma-separated)")
    p.add_argument("--peaks", type=int, default=5, help="Number of music peaks to detect")
    args = p.parse_args()

    clips_dir = Path(args.clips).expanduser().resolve()
    music_path = Path(args.music).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()

    if not clips_dir.is_dir():
        sys.exit(f"❌ Clips folder not found: {clips_dir}")
    if not music_path.is_file():
        sys.exit(f"❌ Music file not found: {music_path}")

    # === 1. Gather clip files ===
    exts = {e.strip().lower() for e in args.ext.split(",")}
    clip_paths = sorted([p for p in clips_dir.iterdir()
                         if p.is_file() and p.suffix.lower().lstrip(".") in exts])
    if not clip_paths:
        sys.exit(f"❌ No clips found in {clips_dir} matching {exts}")

    print(f"📁 Found {len(clip_paths)} clips in {clips_dir}")
    print(f"🎵 Music: {music_path.name}")
    print(f"📂 Output: {out_dir}\n")

    # === 2. Probe each clip ===
    print(f"⏳ Probing clips (this takes ~{len(clip_paths) * 2}s)...")
    clips = []
    for i, cp in enumerate(clip_paths, 1):
        sys.stdout.write(f"\r  [{i}/{len(clip_paths)}] {cp.name[:50]:<50}")
        sys.stdout.flush()
        info = probe_clip(cp)
        info["__path"] = cp
        clips.append(info)
    print()

    # === 3. Music peaks ===
    print(f"⏳ Analyzing music peaks...")
    music = music_peaks(music_path, n=args.peaks)

    # === 4. Print audit table ===
    print(f"\n{'='*100}\n📋 CLIPS AUDIT\n{'='*100}")
    print(f"{'#':<3} {'name':<55} {'dur':>7} {'fps':>5} {'res':>10} {'luma':>5} {'sat':>5} {'D-Log'}")
    print(f"{'-'*100}")
    for i, c in enumerate(clips, 1):
        if "error" in c:
            print(f"{i:<3} {c['name'][:55]:<55} ERROR: {c['error']}")
            continue
        print(f"{i:<3} {c['name'][:55]:<55} "
              f"{c.get('duration', 0):>7.2f} {c.get('fps', 0):>5.1f} "
              f"{c.get('width', 0)}x{c.get('height', 0):>4} "
              f"{c.get('luma', 0):>5.1f} {c.get('sat', 0):>5.1f} "
              f"{'⚠ YES' if c.get('dlog') else '   no'}")

    # === 5. Music peaks ===
    print(f"\n{'='*100}\n🎵 MUSIC ({music['duration']:.1f}s)\n{'='*100}")
    if music.get("peaks"):
        print(f"  Detected {len(music['peaks'])} emotional peaks (use as ACT_TRANSITIONS):")
        for t, lvl in zip(music["peaks"], music.get("peak_levels", [])):
            mm, ss = int(t // 60), t % 60
            print(f"    t = {mm}:{ss:05.2f} ({t:7.2f}s)  RMS={lvl:6.1f}dB")
    else:
        print(f"  ⚠ Could not detect peaks automatically. Open the track in any DAW or listen to find them.")
        print(f"    {music.get('note', '')}")

    # === 6. Write project files ===
    print(f"\n{'='*100}\n📝 GENERATING PROJECT FILES\n{'='*100}")
    project_py = write_my_project(out_dir, clips, music, music_path, args.title, args.subtitle)
    print(f"  ✓ {project_py}")
    mix_py = write_mix_script(out_dir, music_path, len(clips))
    if mix_py:
        print(f"  ✓ {mix_py}")

    # === 7. Next steps ===
    print(f"\n{'='*100}\n🚀 NEXT STEPS\n{'='*100}")
    print(f"""
  1. Open {project_py} and refine the EDIT list (order, durations, speeds, SFX)
  2. Validate before render:
       python3 {SKILL_ROOT}/scripts/validate_edit.py {project_py}
  3. Render preview (5-8 min):
       QUALITY=preview python3 {project_py}
  4. Audit timings vs music peaks:
       python3 {SKILL_ROOT}/scripts/audit_timings.py {project_py}
  5. Iterate (one category of change at a time)
  6. When happy, render 4K (30-45 min):
       python3 {SKILL_ROOT}/scripts/validate_cache.py {out_dir.name}  # purge stale preview cache
       QUALITY=final python3 {project_py}
""")


# Minimal scaffold used if render_template.py is missing
MINIMAL_SCAFFOLD = '''"""@@PROJECT_NAME@@ — generated by bootstrap_project.py. EDIT this file!"""
# CLIPS:  @@CLIPS_DIR@@
# MUSIC:  @@MUSIC_PATH@@
# TITLE:  @@TITLE@@ — @@SUBTITLE@@
# ACT_TRANSITIONS: @@ACT_TRANSITIONS@@

EDIT = [
@@EDIT_LIST@@
]

if __name__ == "__main__":
    print("⚠ Minimal scaffold — copy real render_template.py from the skill")
'''


if __name__ == "__main__":
    main()
