#!/usr/bin/env python3
"""
Drone Cinematic Montage — TEMPLATE
Copy this file, replace paths + EDIT list, then iterate.

Usage:
  QUALITY=preview python3 my_montage.py    # 640x360, ~5min
  QUALITY=final   python3 my_montage.py    # 4K 3840x2160, ~30-45min

See ../SKILL.md and ../docs/ for the full workflow.
"""
import os, subprocess, json, shutil, sys, re

# ============================================================
# Paths — REPLACE these for your project
# ============================================================
PROJECT_NAME = "myproject"
CLIPS   = "/path/to/your/drone/clips"
MUSIC   = "/path/to/your/music.mp3"

FFMPEG  = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

# Optional LUT — set to None to disable
LUT_SRC = None
# LUT_SRC = "/path/to/lut.cube"

# Optional fonts for title/credits PNG generation
FONT       = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"

# ============================================================
# Quality mode
# ============================================================
QUALITY = os.environ.get("QUALITY", "preview")
TMP = f"/tmp/{PROJECT_NAME}"

if QUALITY == "final":
    OUTPUT = f"/path/to/output/{PROJECT_NAME}_final.mp4"
    OUT_W, OUT_H = 3840, 2160
    CRF_SUB, CRF_FINAL = 20, 19
    PRESET_SUB, PRESET_FINAL = "fast", "medium"
else:
    OUTPUT = f"/path/to/output/{PROJECT_NAME}_preview.mp4"
    OUT_W, OUT_H = 640, 360
    CRF_SUB, CRF_FINAL = 26, 24
    PRESET_SUB, PRESET_FINAL = "ultrafast", "veryfast"

SCALE = OUT_W / 3840.0
LUT     = f"{TMP}/lut.cube" if LUT_SRC else None
LUT_STRENGTH = 0.50
SAT_MULT     = 0.90
CONTRAST     = 1.05
GRAIN_STRENGTH = 3
FPS = 30

# Music sync — replace with your music peaks
ACT_TRANSITIONS = [18.0, 37.0, 74.0, 110.0, 129.0]

# ============================================================
# EDIT list — REPLACE with your clips
# ============================================================
# Tuple: (fname, src_start, output_dur, speed, sfx, reframe, extra)
# - src_start: seconds into source clip
# - output_dur: seconds in OUTPUT timeline
# - speed: float (0.85=slowmo) or (s_start, s_end) tuple for ramp
# - sfx: see make_sfx() — "ambient", "lapping", "birds", "whoosh", "boom", etc.
# - reframe: (zoom_start, zoom_end) for Ken Burns, or None
# - extra: "hflip" to mirror horizontally, or None
EDIT = [
    # ACT 0 — opening
    ("CLIP_001.MP4", 0.3, 4.0, 0.85,         "ambient", (1.0, 1.05), None),
    ("CLIP_002.MP4", 4.0, 8.0, (0.5, 0.7),   "lapping", None,        None),
    ("CLIP_003.MP4", 0.0, 6.0, 0.9,          "birds",   (1.06, 1.0), None),

    # ACT 1 — establish
    ("CLIP_004.MP4", 11.0, 5.0, (0.8, 1.2),  "whoosh",  None,        None),
    # ... add your clips
]

# ============================================================
# Outro — REPLACE
# ============================================================
OUTRO = ("CLIP_OUTRO.MP4", 3.0, 8.0, 0.7, "outro_ambient", (1.0, 1.05))

# ============================================================
# Per-clip color overrides — start empty, fill as you iterate
# ============================================================
CLIP_GRADE = {
    # "CLIP_002": {"lut": 0.45, "sat": 1.10, "exposure_fix": True},
    # "CLIP_006": {"lut": 0.40, "sat": 0.78},
}

# ============================================================
# Title + outro overlays
# ============================================================
TITLE_MAIN_TEXT = "YOUR TITLE"
TITLE_SUB_TEXT  = "Location · Date"
OUTRO_MAIN_TEXT = "THANK YOU"
OUTRO_SUB_TEXT  = "See you soon"

# ============================================================
# The rest of the script (process_clip, process_subseg, make_sfx,
# render_xfade_pair, generate_*_png, main) — copy from examples/interlaken_v16.py
# and adapt as needed.
# ============================================================

# TODO: Implement these by copying from examples/interlaken_v16.py:
#   - def get_fps(path)
#   - def get_luma(path, start, dur)
#   - def resolve_segments(speed, out_dur, reframe, n_sub=5)
#   - def build_crop_filter(zs, ze, src_dur, src_fps=30)
#   - def S(x)  -- scale helper
#   - def _draw_plain(img_size, text_items)
#   - def generate_title_png()
#   - def generate_outro_png()
#   - def generate_credits_png()
#   - def make_sfx(sfx_type, dur, out_path)
#   - def make_sting(out_path, dur=1.6)
#   - def render_xfade_pair(subs_a, subs_b, transition_type, duration, idx)
#   - def process_subseg(...)
#   - def process_clip(idx, fname, src_start, out_dur, speed, sfx_type, reframe, extra=None)
#   - def process_outro()
#   - def process_end_credits()
#   - def main()
#
# Or just copy interlaken_v16.py wholesale and modify the top constants + EDIT list.

if __name__ == "__main__":
    raise NotImplementedError(
        "This is a template. Copy examples/interlaken_v16.py and customize."
    )
