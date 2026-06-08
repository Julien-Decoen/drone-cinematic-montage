#!/usr/bin/env python3
"""render_template.py — V25-grade cinematic drone montage template.

Generated/copied by bootstrap_project.py — placeholders @@XXX@@ get substituted
when bootstrapping a new project. You can ALSO copy this file manually and
fill in the values yourself.

Features included (V25):
  - 7-field EDIT tuple (fname, src_start, out_dur, speed, sfx, reframe, extra)
  - extras: "hflip", "reverse", "fadeout", or "hflip,reverse" (comma-separated)
  - Frame-precise rendering (-frames:v N instead of -t dur → zero cumulative drift)
  - clamp_speed_for_fps for ramps when source is insufficient
  - CLIP_GRADE per-clip overrides (lut/sat/gamma/exposure_fix)
  - exposure_fix S-curve + warm shift (preserves deep blacks on cold-cast clips)
  - minterpolate fps=60 for smooth slowmo on 30fps sources
  - Title/outro PNG overlays generated via PIL
  - Per-clip SFX layering (synthetic via lavfi — for real MP3 SFX, use audio_mix_template.py)

USAGE:
    QUALITY=preview python3 my_project.py     # 640×360, ~5-8 min
    QUALITY=final   python3 my_project.py     # 3840×2160, ~30-45 min

VALIDATE BEFORE RENDERING:
    python3 .../scripts/validate_edit.py my_project.py
    python3 .../scripts/audit_timings.py  my_project.py
    python3 .../scripts/validate_cache.py /tmp/<project>  --quality final
"""
import os
import subprocess
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# PROJECT CONFIG  (bootstrap fills these via @@XXX@@ markers)
# ============================================================

PROJECT_NAME = "@@PROJECT_NAME@@"
CLIPS    = "@@CLIPS_DIR@@"
MUSIC    = "@@MUSIC_PATH@@"
TITLE    = "@@TITLE@@"
SUBTITLE = "@@SUBTITLE@@"
TMP      = "@@TMP_DIR@@"

QUALITY  = os.environ.get("QUALITY", "preview")
FPS      = 30
FFMPEG   = shutil.which("ffmpeg")  or "/opt/homebrew/bin/ffmpeg"
FFPROBE  = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

# Optional LUT (Orange-Teal etc) — leave empty string to skip
LUT_SRC = ""  # e.g. "/Users/me/luts/Orange_Teal.cube"

# Output paths
OUT_DIR = Path(MUSIC).parent  # default: same folder as music
if QUALITY == "final":
    OUTPUT  = str(OUT_DIR / f"{PROJECT_NAME}_master.mp4")
    OUT_W, OUT_H = 3840, 2160
    CRF_SUB, CRF_FINAL = 20, 19
    PRESET_SUB, PRESET_FINAL = "fast", "medium"
else:
    OUTPUT  = str(OUT_DIR / f"{PROJECT_NAME}_preview.mp4")
    OUT_W, OUT_H = 640, 360
    CRF_SUB, CRF_FINAL = 26, 24
    PRESET_SUB, PRESET_FINAL = "ultrafast", "veryfast"

SCALE = OUT_W / 3840.0

# Color baseline (override per-clip via CLIP_GRADE)
LUT_STRENGTH = 0.50
SAT_MULT     = 0.90
CONTRAST     = 1.05
GAMMA_DARK   = 1.0
DARK_THRESH  = 85
BRIGHT_MULT  = 0.30
BRIGHT_MIN   = -0.04
BRIGHT_MAX   = 0.08

os.makedirs(TMP, exist_ok=True)

# ============================================================
# MUSIC SYNC — peaks in seconds (use bootstrap_project.py to detect)
# ============================================================
ACT_TRANSITIONS = [@@ACT_TRANSITIONS@@]

# ============================================================
# EDIT LIST — the heart of the project
# Tuple: (fname, src_start, output_dur, speed, sfx, reframe, extra)
#   - src_start: where to start reading the source clip (s)
#   - output_dur: duration in the OUTPUT timeline (s)
#   - speed: float (0.85 = slowmo) | tuple (s_start, s_end) for ease-in-out ramp
#   - sfx: "ambient"|"lapping"|"birds"|"train"|"whoosh"|"boom"|"riser"|"cascade_fade"|None
#   - reframe: (zoom_start, zoom_end) Ken Burns push | None
#   - extra: None | "hflip" | "reverse" | "fadeout" | "hflip,reverse" (comma-sep)
# ============================================================
EDIT = [
@@EDIT_LIST@@
]

# ============================================================
# CLIP_GRADE — per-clip color overrides
# Key = substring of filename (first match wins)
# Values:
#   lut: 0.0-1.0 (LUT blend strength)
#   sat: 0.5-1.3 (saturation multiplier)
#   gamma: 0.9-1.3 (gamma lift — use for dark clips)
#   exposure_fix: True → applies S-curve + warm shift (preserves deep blacks)
# ============================================================
CLIP_GRADE = {
    # "0084_D-00.01.21": {"lut": 0.45, "sat": 0.88, "exposure_fix": True},
}

# ============================================================
# Title/outro overlays
# ============================================================
def S(n): return max(1, int(n * SCALE))

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
TITLE_MAIN_PNG = f"{TMP}/title_main.png"
TITLE_SUB_PNG  = f"{TMP}/title_sub.png"
OUTRO_MAIN_PNG = f"{TMP}/outro_main.png"
OUTRO_SUB_PNG  = f"{TMP}/outro_sub.png"


def make_title_png(text: str, out_path: str, size_px: int, font_path: str = FONT_DIDOT):
    """Render text as PNG with transparent bg + white text + drop shadow."""
    font = ImageFont.truetype(font_path, S(size_px))
    bbox = ImageDraw.Draw(Image.new("RGBA", (10, 10))).textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + S(40)
    h = bbox[3] - bbox[1] + S(40)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Subtle shadow
    d.text((S(20) + S(3), S(20) + S(3)), text, font=font, fill=(0, 0, 0, 180))
    d.text((S(20), S(20)), text, font=font, fill=(255, 255, 255, 255))
    img.save(out_path)


def make_overlays():
    make_title_png(TITLE,    TITLE_MAIN_PNG, 156, FONT_DIDOT)
    make_title_png(SUBTITLE, TITLE_SUB_PNG,  48,  FONT)
    make_title_png("THANK YOU",   OUTRO_MAIN_PNG, 156, FONT_DIDOT)
    make_title_png("See you soon", OUTRO_SUB_PNG, 48, FONT)


# ============================================================
# Helpers
# ============================================================
def run(cmd, tag=""):
    """Run ffmpeg, retry up to 3 times on transient failures."""
    for attempt in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return
        if attempt == 2:
            print(f"❌ [{tag}] {r.stderr[-500:]}")
            raise SystemExit(1)


def probe_duration(path: str) -> float:
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def clamp_speed_for_fps(speed, out_dur: float, src_avail: float):
    """Clamp speed so out_dur * speed ≤ src_avail. Returns clamped speed.
    Critical for ramps where source might be too short."""
    if isinstance(speed, (tuple, list)):
        avg = (speed[0] + speed[1]) / 2.0
        if avg * out_dur > src_avail:
            max_avg = src_avail / out_dur * 0.99
            scale = max_avg / avg
            return (speed[0] * scale, speed[1] * scale)
        return speed
    if speed * out_dur > src_avail:
        return src_avail / out_dur * 0.99
    return speed


def get_grade(fname: str) -> dict:
    for key, override in CLIP_GRADE.items():
        if key in fname:
            return override
    return {}


# ============================================================
# Sub-segment renderer (one EDIT entry → one MP4 sub-clip)
# Frame-precise: outputs exactly int(round(out_dur * FPS)) frames
# ============================================================
def process_subseg(clip_path: str, ss: float, src_dur: float, sub_out_dur: float,
                   speed: float, extra: str | None, grade: dict,
                   out_path: str, motion_blur: bool):
    extras = (extra or "").split(",") if extra else []
    hflip_chain   = "hflip,"   if "hflip"   in extras else ""
    reverse_chain = "reverse," if "reverse" in extras else ""
    # Fadeout (V25.17): 1s fade-to-black at end of plan
    fadeout_filter = (f",fade=t=out:st={sub_out_dur-1.0:.3f}:d=1.0:color=black"
                      if "fadeout" in extras else "")

    # Scale to output resolution
    scale_chain = f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,crop={OUT_W}:{OUT_H},"

    # Motion-compensated interpolation for slowmo
    interp_chain = (
        f"minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
        if motion_blur else ""
    )

    # Speed via setpts
    pts = 1.0 / float(speed)

    # Grading parameters
    saturation = SAT_MULT * grade.get("sat", 1.0)
    gamma      = grade.get("gamma", GAMMA_DARK)
    contrast   = CONTRAST
    brightness = 0.0
    lut_strength = grade.get("lut", LUT_STRENGTH)
    exposure_fix = grade.get("exposure_fix", False)

    a_str, b_str = 1.0 - lut_strength, lut_strength

    # Grading chain
    if exposure_fix:
        grade_chain = (
            f"[bl]curves=master='0/0 0.05/0.02 0.20/0.27 0.50/0.62 0.80/0.88 1/1':all='0/0 1/1',"
            f"colorbalance=bs=-0.05:bm=-0.03:bh=-0.02,"
            f"eq=saturation={saturation:.3f}:gamma={gamma:.3f}:contrast=1.080,"
            f"vignette=PI/4{fadeout_filter}[out]"
        )
    else:
        grade_chain = (
            f"[bl]eq=brightness={brightness:.4f}:contrast={contrast:.3f}:saturation={saturation:.3f}:gamma={gamma:.3f},"
            f"vignette=PI/4{fadeout_filter}[out]"
        )

    lut_filter = f"lut3d={LUT_SRC}" if LUT_SRC and os.path.exists(LUT_SRC) else "null"

    fc = (
        f"[0:v]"
        f"{hflip_chain}"
        f"{reverse_chain}"
        f"{scale_chain}"
        f"{interp_chain}"
        f"setpts={pts:.5f}*PTS,"
        f"split[a][b];"
        f"[b]{lut_filter}[lb];"
        f"[a][lb]blend=all_expr='A*{a_str:.3f}+B*{b_str:.3f}'[bl];"
        f"{grade_chain}"
    )

    # V25 FRAME-PRECISE: force exact frame count
    out_frames = int(round(sub_out_dur * FPS))
    run([FFMPEG, "-y",
         "-ss", f"{ss:.3f}", "-t", f"{src_dur + 0.5:.3f}",
         "-i", clip_path,
         "-filter_complex", fc,
         "-map", "[out]",
         "-frames:v", str(out_frames),    # exact frame count = zero drift
         "-c:v", "libx264", "-preset", PRESET_SUB, "-crf", str(CRF_SUB),
         "-r", str(FPS), "-pix_fmt", "yuv420p", "-an",
         out_path],
        tag=f"subseg {os.path.basename(out_path)}")


def process_clip(idx: int, entry: tuple) -> list[str]:
    """Render one EDIT entry. Handles ramps by splitting into sub-segments.
    Returns list of cached sub-clip paths."""
    fname, src_start, out_dur, speed, sfx, reframe, extra = (list(entry) + [None] * 7)[:7]
    clip_path = str(Path(CLIPS) / fname)
    src_dur_total = probe_duration(clip_path)
    grade = get_grade(fname)

    # Clamp speed if source insufficient
    src_avail = src_dur_total - src_start
    speed = clamp_speed_for_fps(speed, out_dur, src_avail)

    cached = []
    if isinstance(speed, (tuple, list)):
        # Ramp: split into n_sub sub-segments with linear-interpolated speeds
        n_sub = 5
        s_start, s_end = speed
        sub_dur = out_dur / n_sub
        ss = src_start
        for j in range(n_sub):
            sub_speed = s_start + (s_end - s_start) * (j + 0.5) / n_sub
            sub_src = sub_dur * sub_speed
            out_path = f"{TMP}/clip_{idx:02d}_{j}.mp4"
            if not os.path.exists(out_path):
                process_subseg(clip_path, ss, sub_src, sub_dur, sub_speed, extra,
                               grade, out_path,
                               motion_blur=(sub_speed < 0.9))
            cached.append(out_path)
            ss += sub_src
    else:
        out_path = f"{TMP}/clip_{idx:02d}_0.mp4"
        if not os.path.exists(out_path):
            src_used = out_dur * speed
            process_subseg(clip_path, src_start, src_used, out_dur, speed, extra,
                           grade, out_path,
                           motion_blur=(speed < 0.9))
        cached.append(out_path)
    return cached


# ============================================================
# Synthetic SFX via lavfi (replace with audio_mix_template.py for real MP3 SFX)
# ============================================================
def make_sfx(kind: str, dur: float, out_path: str):
    """Generate synthetic SFX. For real MP3-based SFX, use the external audio mix script."""
    if kind == "ambient":
        af = (f"sine=frequency=80:duration={dur},"
              f"volume=0.30")
    elif kind == "whoosh":
        af = (f"anoisesrc=duration={dur}:amplitude=0.4,"
              f"bandpass=f=800:width_type=h:w=600,"
              f"afade=t=in:st=0:d=0.1,afade=t=out:st={dur-0.3:.2f}:d=0.3,"
              f"volume=0.7")
    elif kind == "boom":
        af = (f"sine=frequency=50:duration={dur},"
              f"afade=t=in:st=0:d=0.2,afade=t=out:st={dur-0.6:.2f}:d=0.6,"
              f"volume=1.2")
    else:
        # Default: silent placeholder
        af = f"anullsrc=duration={dur}"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", af.split(",")[0],
         "-af", ",".join(af.split(",")[1:]) if "," in af else "anull",
         "-t", f"{dur:.3f}", "-c:a", "aac", "-b:a", "128k", out_path],
        tag=f"sfx {kind}")


# ============================================================
# Main pipeline
# ============================================================
def main():
    print(f"\n{'='*70}")
    print(f"  {PROJECT_NAME} — {OUT_W}×{OUT_H} [{QUALITY}]")
    print(f"  Clips: {CLIPS}")
    print(f"  Music: {MUSIC}")
    print(f"  Plans: {len(EDIT)} · Output: {OUTPUT}")
    print(f"{'='*70}\n")

    make_overlays()

    # 1. Render each EDIT plan
    all_sub_clips = []
    for i, entry in enumerate(EDIT):
        print(f"  [{i+1}/{len(EDIT)}] {entry[0][:50]:<50}")
        all_sub_clips += process_clip(i, entry)

    # 2. Concat all sub-clips
    concat_file = f"{TMP}/assembly_main.txt"
    with open(concat_file, "w") as f:
        for c in all_sub_clips:
            f.write(f"file '{c}'\n")
    main_video = f"{TMP}/main_video.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
         "-c:v", "copy", "-an", main_video], tag="concat main")

    # 3. Final encode with audio
    print(f"\n  Final encode (with music)…")
    run([FFMPEG, "-y", "-i", main_video, "-i", MUSIC,
         "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", PRESET_FINAL, "-crf", str(CRF_FINAL),
         "-c:a", "aac", "-b:a", "192k",
         "-pix_fmt", "yuv420p", "-shortest", OUTPUT],
        tag="final")

    size_mb = os.path.getsize(OUTPUT) // 1024 // 1024
    dur = probe_duration(OUTPUT)
    print(f"\n{'='*70}")
    print(f"  ✓ [{QUALITY}]  {OUTPUT}")
    print(f"  {OUT_W}×{OUT_H} · {dur:.2f}s · {size_mb} MB")
    print(f"{'='*70}\n")
    if QUALITY == "preview":
        print(f"  → For 4K final:  QUALITY=final python3 {Path(__file__).name}\n")


if __name__ == "__main__":
    main()
