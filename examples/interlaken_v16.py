#!/usr/bin/env python3
"""
Interlaken Cinematic Montage — V3
- Pre-credits removed; clip [32] becomes outro with MERCI/À bientôt overlay
- INTERLAKEN title overlay on clip [09] (second shot) instead
- Music sync millimétré : 13 cuts alignés sur les peaks (18.5, 27, 37.5, 46, 54.5,
  63.5, 74, 91.5, 109.5, 118.5, 129, 137.5, 146, 154.5)
- Cascade ramp+hold + freeze frame 0.3s at reveal
- Finale ramp+hold (0.5→0.3 then hold 0.3x)
- [06] village rotate uses src_start=8.5s to capture tilt-up reveal
- [22] gare src_start=3.5, [31] parking src_start=3.0
- ADD [24] rails 0100-2 (new clip in ACT 2)
- Letterbox 2.35:1 (264px bars top/bottom)
- Film grain subtle
- Motion blur via tblend on slowmo clips
- Audio stings boom on 5 act transitions
- End credits black screen (Lou_Juicy 2026)
"""
import os, subprocess, json, shutil, sys, re

FFMPEG  = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
CLIPS   = "/Users/juicy/Documents/drone/Interlaken 26/export"
MUSIC   = "/Users/juicy/Documents/drone/Interlaken 26/nastelbom-cinematic-ambient-501722.mp3"
# ============================================================
# Quality mode: "preview" (720p, fast) or "final" (4K, slow)
# ============================================================
QUALITY = os.environ.get("QUALITY", "preview")

TMP     = "/tmp/interlaken_v16"
LUT     = f"{TMP}/lut.cube"
LUT_SRC = ("/Users/juicy/Documents/luts/The Ultimate Bundle - HV Presets/"
           "1 - The Ultimate Preset Bundle/Orange Teal/"
           "LUT For PR-AE-FCPX (Cube)/Orage & Teal  (9).cube")  # V5: switched #5 → #9
FONT      = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
TITLE_MAIN_PNG = f"{TMP}/title_main.png"     # V11: split title into MAIN + SUB
TITLE_SUB_PNG  = f"{TMP}/title_sub.png"
OUTRO_MAIN_PNG = f"{TMP}/outro_main.png"     # V11: split outro into MAIN + SUB
OUTRO_SUB_PNG  = f"{TMP}/outro_sub.png"
CREDITS_PNG = f"{TMP}/credits.png"

if QUALITY == "final":
    OUTPUT  = "/Users/juicy/Documents/drone/Interlaken 26/interlaken_cinematic_v16.mp4"
    OUT_W, OUT_H = 3840, 2160
    LETTERBOX = 0
    CRF_SUB = 20
    CRF_FINAL = 19
    PRESET_SUB = "fast"
    PRESET_FINAL = "medium"
else:
    OUTPUT  = "/Users/juicy/Documents/drone/Interlaken 26/interlaken_cinematic_v16_preview.mp4"
    OUT_W, OUT_H = 640, 360
    LETTERBOX = 0
    CRF_SUB = 26
    CRF_FINAL = 24
    PRESET_SUB = "ultrafast"
    PRESET_FINAL = "veryfast"

SCALE = OUT_W / 3840.0
TARGET_L = 130.0
LUT_STRENGTH = 0.50            # V10: 0.88 → 0.50 (natural look — subtle LUT)
GRAIN_STRENGTH = 3             # V11: 6 → 3 (anti-flicker)
BRIGHT_MULT = 0.3
BRIGHT_MIN  = -0.04
BRIGHT_MAX  = 0.08
GAMMA_DARK  = 1.0
DARK_THRESH = 85
SAT_MULT    = 0.90             # V10: 1.10 → 0.90 (natural — less punch)
CONTRAST    = 1.05             # V10: 1.06 → 1.05
FPS         = 30

# === Music swell peaks (for transitions & stings) ===
# V4: user-identified music transitions (perceived major shifts)
ACT_TRANSITIONS = [18.0, 37.0, 74.0, 110.0, 129.0]
INTERNAL_PEAKS  = [27.0, 54.5, 63.5, 84.0, 91.5, 100.5, 118.5, 137.5, 146.0, 154.5]

# === Outro: clip [32] with MERCI overlay ===
# (fname, src_start, output_dur, speed, sfx, reframe)
OUTRO = (
    # V16: footsteps → outro_ambient (drone bass + footsteps + wind layered)
    "DJI_20260516153528_0105_D-00.01.29.534-00.01.40.733-seg3.MP4",
    3.0, 11.0, 0.7, "outro_ambient", (1.0, 1.05)
)

# === Main montage ===
# Each entry: (fname, src_start, output_dur, speed, sfx, reframe)
# speed: float | (s_start, s_end) ramp | list of (sub_src, sub_speed) tuples (custom)
# special_kind: "freeze_then_ramp_hold", "ramp_hold" — custom processing
EDIT = [
    # ===== ACT 0 — ÉVEIL (0:00 → 0:18, 18s) =====
    # #1 chalet — hflip to break duplicate with #2
    ("DJI_20260516153045_0102_D-00.00.00.000-00.00.05.771.MP4",       0.3, 4.0,  0.85,         "ambient",  (1.0, 1.05), "hflip"),
    # #2 lac brumeux — V16: SFX "lapping" (eau qui clapote) au lieu d'ambient
    ("DJI_20260515183225_0090_D-00.00.08.762-00.00.32.060.MP4",       4.0, 8.0,  (0.5, 0.7),   "lapping",  None,        None),
    # #3 reveal — V6: speed 0.9x (was 0.7x)
    ("DJI_20260514175058_0084_D-00.00.20.048-00.01.00.144-seg1.MP4",  0.0, 6.0,  0.9,          "birds",    (1.06, 1.0), None),

    # ===== ACT 1 — VILLAGES PROCHES (0:18 → 0:37, 19s) =====
    # #4 routes — V6: ramp 0.8→1.2 (was 0.5→1.0, more dynamic reveal)
    ("DJI_20260514175058_0084_D-00.01.35.758-00.01.52.976-seg4.MP4", 11.0, 5.0,  (0.8, 1.2),   "whoosh",   None,        None),
    # #5 top-down — V6: src=2 (was 4)
    ("DJI_20260514175058_0084_D-00.01.21.489-00.01.28.211-seg3.MP4",  2.0, 4.0,  0.6,          "birds",    (1.0, 1.05), None),
    # V6 SWAP: pan reveal FIRST (was #7), reveal lac SECOND (was #6)
    # NEW #6 = 0084-5 pan reveal — 4s (was 6s)
    ("DJI_20260514175058_0084_D-00.03.01.139-00.03.31.093-seg5.MP4", 18.0, 4.0,  0.5,          "ambient",  (1.0, 1.07), None),
    # NEW #7 = 0085-1 reveal lac — 6s, src=7.5 (1s earlier), speed 0.9x
    ("DJI_20260514175441_0085_D-00.00.17.296-00.00.31.614-seg1.MP4",  7.5, 6.0,  0.9,          "ambient",  None,        None),

    # ===== ACT 2 — DÉCOUVERTE / MOUVEMENT (0:37 → 1:14, 37s) =====
    # #8 0086 high overhead — src=9 (less trees, more lake)
    ("DJI_20260514175834_0086_D-00.00.39.881-00.00.57.613.MP4",       9.0, 6.0,  0.7,          "whoosh",   None,        None),
    # #9 0099 gare trains — V15: src 3.5→0 (anti drone-drift)
    ("DJI_20260516142501_0099_D-00.00.07.570-00.00.27.589.MP4",       0.0, 6.0,  (1.0, 1.4),   "train",    None,        None),
    # #10 0100-seg1 — V16: speed=1.25x (rotation matched), src=4.55 → exit perp src=10.8
    ("DJI_20260516142741_0100_D-00.00.01.661-00.00.25.015-seg1.MP4",  4.55, 5.0,  1.25,         "train_whistle", (1.0, 1.04), None),
    # #11 NEW — V16: speed=0.74x (rotation matched), src=4.0 perp pont vertical
    ("DJI_20260516142244_0098_D-00.00.05.498-00.00.27.990-seg1.MP4",  4.0, 5.5,  0.74,         "ambient",  (1.0, 1.04), None),
    # #12 0098-seg3 urban→cascade — V15: réduit moitié, GARDE LA FIN cascade
    # src=10.5, out=4.75 @ 0.85x → src_consumed=4.04 → ends at 14.54 (= fin du rush ✓)
    ("DJI_20260516142244_0098_D-00.01.48.108-00.02.02.744-seg3.MP4", 10.5,  4.75, 0.85,        "ambient",  (1.0, 1.08), None),
    # #13 0097-1 bâtiments+rivière (ex-#12)
    ("DJI_20260516142049_0097_D-00.00.22.142-00.00.42.017-seg1.MP4",  3.0, 11.0, (0.6, 1.0),   "whoosh",   None,        None),

    # ===== ACT 3 — CASCADE (1:14 → 1:49.5, 35.5s) =====
    # V6: cascade shorter (14s) + SFX fade-out mid-clip
    ("DJI_20260515183659_0092_D-00.00.35.454-00.00.56.207.MP4",       0.0, 14.0, 1.0,          "cascade_fade",  None,    None),
    # #15 ROTATION 0091-seg2 — V15: speed 0.85→1.0 (real-time, fix saccadé)
    ("DJI_20260515183417_0091_D-00.00.21.529-00.00.38.370-seg2.MP4",  0.0, 10.0, 1.0,          "ambient",  (1.0, 1.05), None),
    # #15 0094 route → lac — V11: src=3 (was 1) → lake clearly visible at end
    ("DJI_20260515184006_0094_D-00.01.05.439-00.01.19.118.MP4",       3.0, 12.0, (0.6, 1.0),   "whoosh",   None,        None),

    # ===== ACT 4 — LAC (1:49.5 → 2:09, 19.5s) =====
    # V6: act 4 starts at 109.5 (music calms), ends at 129
    # #17 0095-1 voiliers (ex-#16) — V14: src 3→0 (utilise début du rush)
    ("DJI_20260515184716_0095_D-00.00.01.905-00.00.19.828-seg1.MP4",  0.0, 7.5,  0.5,          "sail",     (1.0, 1.05), None),
    # #17 0096 marina — V6: 6.5s (+1s start, +1s end), src=3 (1s earlier)
    ("DJI_20260515185059_0096_D-00.00.48.241-00.00.57.769.MP4",       3.0, 6.5,  0.8,          "ambient",  None,        None),
    # #18 0095-2 voiliers angle — V7: extended to 5.5s (was 2.5), replaces dropped #19
    ("DJI_20260515184716_0095_D-00.00.51.921-00.01.07.686-seg2.MP4",  2.0, 5.5,  0.6,          "sail",     (1.0, 1.04), None),
    # V7: #19 parking DROPPED (was not adding much)

    # ===== ACT 5 — CHÂTEAUX FINALE (2:09 → 2:40, 31s) — moins de slowmo =====
    # V5: act 5 starts 130 (peak), #20 at 130, #21 at 138 (peaks)
    # #20 0104 reflet (was #19) — V14: src 2→8.5 (fin du rush, clip dur 15.28)
    ("DJI_20260516153355_0104_D-00.00.31.754-00.00.46.302.MP4",       8.5, 8.0,  0.85,         "ambient",  (1.05, 1.0), None),
    # #21 0103-seg5 château REMPLACE 0103-seg1 — V14: prend fin du rush (clip dur 11.68)
    # src=5.3 + out=8 @ 0.8x → src_consumed=6.4 → ends at 11.7 (= end of clip) ✓
    ("DJI_20260516153148_0103_D-00.01.11.091-00.01.22.741-seg5.MP4",  5.3, 8.0,  0.8,          "boom",     (1.0, 1.07), None),
    # #22 0105-1 FINALE — V14: ramp (0.5, 1.5). V16: SFX "riser" sur l'accélération
    ("DJI_20260516153528_0105_D-00.00.01.915-00.00.26.750-seg1.MP4",  2.0, 15.4, (0.5, 1.5),   "riser",    None,        None),
]

# Total: 4+8.5+6 + 5+3.5+4+6.5+5.5+3 + 6+2.5+9+10.5 + 9+8.5+14+4 + 9+3.5+4+3 + 8.5+8.5+14 = 168s? let me check
# Act 0: 18.5, Act 1: 27.5, Act 2: 28, Act 3: 35.5, Act 4: 19.5, Act 5: 31 → 160.0 ✓
# + outro 7s = 167s of video
# + end credits 9s = 176s


# ============================================================
# Helpers
# ============================================================

def run(cmd, check=True, tag=""):
    if tag:
        print(f"    [{tag}]", end=" ")
    print("$", " ".join(str(c) for c in cmd[:5]) + " …")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print("STDERR:", r.stderr[-2500:])
        sys.exit(1)
    return r


def get_fps(path):
    r = subprocess.run([FFPROBE, "-v", "quiet", "-i", path,
                        "-select_streams", "v:0",
                        "-show_entries", "stream=r_frame_rate",
                        "-of", "json"], capture_output=True, text=True)
    try:
        s = json.loads(r.stdout)["streams"][0]["r_frame_rate"]
        n, d = map(int, s.split("/"))
        return n / d
    except Exception:
        return 30.0


def get_luma(path, start, dur):
    cmd = [FFMPEG, "-hide_banner", "-ss", str(start), "-t", str(min(dur, 2.0)),
           "-i", path,
           "-vf", "scale=480:-1,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
           "-an", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    vals = [float(m) for m in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", r.stderr)]
    return sum(vals) / len(vals) if vals else TARGET_L


def clamp_speed_for_fps(speed, fps):
    if fps < 50 and speed < 0.6:
        return 0.6
    return speed


def resolve_segments(speed, out_dur, reframe=None, n_sub=5):
    """Return list of (sub_src_dur, sub_speed, sub_out_dur, (zs, ze)).
       Uses ease-in-out (cosine S-curve) on speed ramps — Premiere-style."""
    import math
    rz1, rz2 = (1.0, 1.0) if reframe is None else reframe
    if isinstance(speed, tuple):
        s1, s2 = speed
        # easeInOut(t) = (1 - cos(pi*t)) / 2 for t in [0,1]
        # Use n_sub sub-segments
        n = n_sub
        sub_out = out_dur / n
        # Speeds evaluated at MIDPOINT of each sub-seg for smoother integration
        speeds = []
        for i in range(n):
            t_mid = (i + 0.5) / n
            ease = (1.0 - math.cos(math.pi * t_mid)) / 2.0
            speeds.append(s1 + (s2 - s1) * ease)
        result = []
        for i, sp in enumerate(speeds):
            sub_zs = rz1 + (rz2 - rz1) * (i / n)
            sub_ze = rz1 + (rz2 - rz1) * ((i + 1) / n)
            result.append((sub_out * sp, sp, sub_out, (sub_zs, sub_ze)))
        return result
    return [(out_dur * speed, speed, out_dur, (rz1, rz2))]


def build_crop_filter(zs, ze, src_dur, src_fps=30):
    """Animated Ken Burns via zoompan. NB: must be placed BEFORE setpts in the
    filter chain since zoompan doesn't respect stretched PTS."""
    if abs(zs - 1.0) < 1e-4 and abs(ze - 1.0) < 1e-4:
        return ""
    # zoompan operates on natural-speed source frames; ramp must span src_dur*fps frames
    total_frames = max(1, int(src_dur * src_fps))
    delta = ze - zs
    z_expr = f"{zs:.5f}{delta:+.6f}*on/{total_frames}"
    return (
        f"zoompan=z='{z_expr}':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={OUT_W}x{OUT_H}:fps={src_fps},"
    )


# ============================================================
# PNG generation
# ============================================================

def S(x):
    """Scale a 4K-design value to current output resolution."""
    return max(1, int(x * SCALE))


def _draw_with_shadow(img_size, text_items, shadow=(3, 4, 200, 5)):
    """text_items: list of (text, font, xy, fill). Returns RGBA layer with soft drop shadow."""
    from PIL import Image, ImageDraw, ImageFilter
    overlay = Image.new("RGBA", img_size, (0, 0, 0, 0))
    sh = Image.new("RGBA", img_size, (0, 0, 0, 0))
    d_sh = ImageDraw.Draw(sh)
    ox, oy, sa, sb = shadow
    for text, font, (x, y), _ in text_items:
        d_sh.text((x + ox, y + oy), text, font=font, fill=(0, 0, 0, sa))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=sb))
    overlay = Image.alpha_composite(overlay, sh)
    d = ImageDraw.Draw(overlay)
    for text, font, xy, fill in text_items:
        d.text(xy, text, font=font, fill=fill)
    return overlay


def _draw_plain(img_size, text_items):
    """Draw text without drop shadow (V11)."""
    from PIL import Image, ImageDraw
    overlay = Image.new("RGBA", img_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for text, font, xy, fill in text_items:
        d.text(xy, text, font=font, fill=fill)
    return overlay


def generate_title_png():
    """V11: split into TITLE_MAIN (INTERLAKEN) + TITLE_SUB (Switzerland · May 2026).
       No drop shadow. Each PNG is sized exactly to its text so we can position
       them independently with separate animations."""
    from PIL import Image, ImageDraw, ImageFont
    f_main = ImageFont.truetype(FONT_DIDOT, S(156), index=0)
    f_sub  = ImageFont.truetype(FONT, S(48), index=4)  # Helvetica Light

    d_tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10), (0,0,0,0)))

    # ----- MAIN -----
    bb_main = d_tmp.textbbox((0, 0), "INTERLAKEN", font=f_main)
    main_w  = bb_main[2] - bb_main[0]
    main_h  = bb_main[3] - bb_main[1]
    pad = S(20)
    W1, H1 = main_w + 2*pad, main_h + 2*pad
    layer1 = _draw_plain((W1, H1), [
        ("INTERLAKEN", f_main, (pad - bb_main[0], pad - bb_main[1]),
         (250, 250, 250, 250)),
    ])
    layer1.save(TITLE_MAIN_PNG)

    # ----- SUB -----
    bb_sub = d_tmp.textbbox((0, 0), "Switzerland · May 2026", font=f_sub)
    sub_w  = bb_sub[2] - bb_sub[0]
    sub_h  = bb_sub[3] - bb_sub[1]
    W2, H2 = sub_w + 2*pad, sub_h + 2*pad
    layer2 = _draw_plain((W2, H2), [
        ("Switzerland · May 2026", f_sub, (pad - bb_sub[0], pad - bb_sub[1]),
         (230, 230, 230, 230)),
    ])
    layer2.save(TITLE_SUB_PNG)
    print(f"  title PNG → MAIN {W1}x{H1} + SUB {W2}x{H2} (no shadow)")


def generate_outro_png():
    """V11: split outro into MERCI + À bientôt. No drop shadow. More spacing."""
    from PIL import Image, ImageDraw, ImageFont
    f_main = ImageFont.truetype(FONT_DIDOT, S(128), index=0)
    f_sub  = ImageFont.truetype(FONT, S(48), index=4)

    d_tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10), (0,0,0,0)))
    pad = S(20)

    # ----- MAIN -----
    bb_main = d_tmp.textbbox((0, 0), "THANK YOU", font=f_main)
    main_w  = bb_main[2] - bb_main[0]
    main_h  = bb_main[3] - bb_main[1]
    W1, H1 = main_w + 2*pad, main_h + 2*pad
    layer1 = _draw_plain((W1, H1), [
        ("THANK YOU", f_main, (pad - bb_main[0], pad - bb_main[1]),
         (250, 250, 250, 250)),
    ])
    layer1.save(OUTRO_MAIN_PNG)

    # ----- SUB -----
    bb_sub = d_tmp.textbbox((0, 0), "See you soon", font=f_sub)
    sub_w  = bb_sub[2] - bb_sub[0]
    sub_h  = bb_sub[3] - bb_sub[1]
    W2, H2 = sub_w + 2*pad, sub_h + 2*pad
    layer2 = _draw_plain((W2, H2), [
        ("See you soon", f_sub, (pad - bb_sub[0], pad - bb_sub[1]),
         (230, 230, 230, 230)),
    ])
    layer2.save(OUTRO_SUB_PNG)
    print(f"  outro PNG → MAIN {W1}x{H1} + SUB {W2}x{H2} (no shadow)")


def generate_credits_png():
    """V5: Didot title + Paki & Hideki line."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font_title = ImageFont.truetype(FONT_DIDOT, S(130), index=0)
    font_sub   = ImageFont.truetype(FONT, S(56), index=4)
    font_body  = ImageFont.truetype(FONT, S(48), index=4)
    font_copy  = ImageFont.truetype(FONT, S(40), index=4)

    cx = OUT_W // 2
    cy = OUT_H // 2

    def center_text(y, text, font, fill=(255, 255, 255, 240)):
        bbox = d.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        d.text((cx - w // 2, y), text, font=font, fill=fill)

    y = cy - S(430)
    center_text(y, "INTERLAKEN", font_title);              y += S(200)
    center_text(y, "Switzerland · May 2026", font_sub, (220, 220, 220, 230));  y += S(170)
    center_text(y, "Trip with Paki & Hideki", font_body, (210, 210, 210, 230));  y += S(120)
    center_text(y, "Music — Nastelbom · \"Cinematic Ambient\"", font_body, (200, 200, 200, 220));  y += S(80)
    center_text(y, "Filmed in Brienz · Iseltwald · Oberhofen", font_body, (200, 200, 200, 220));  y += S(170)
    center_text(y, "© Lou_Juicy 2026", font_copy, (180, 180, 180, 200))

    img.save(CREDITS_PNG)
    print(f"  credits PNG → {CREDITS_PNG} (with Paki & Hideki)")


# ============================================================
# SFX generation (same as V2 + new sting helper)
# ============================================================

def make_sfx(sfx_type, dur, out_path):
    d  = f"{dur:.3f}"
    fo = f"{max(0.05, dur - 0.5):.3f}"

    if sfx_type == "whoosh":
        lavfi = (f"anoisesrc=d={d}:c=pink:r=44100:a=0.55,"
                 f"bandpass=f=900:width_type=h:w=700,"
                 f"afade=t=in:st=0:d=0.05,afade=t=out:st={fo}:d=0.45,"
                 f"volume=1.3")
        return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "boom":
        lavfi = (f"sine=f=50:d={d}:r=44100,"
                 f"volume=3.0,"
                 f"afade=t=in:st=0:d=0.02,"
                 f"afade=t=out:st={max(0.05, dur*0.2):.3f}:d={min(dur*0.75, 3.0):.3f}")
        return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "cascade":
        return run([FFMPEG, "-y",
                    "-f", "lavfi", "-i", f"anoisesrc=d={d}:c=white:r=44100:a=0.65",
                    "-f", "lavfi", "-i", f"sine=f=45:d={d}:r=44100",
                    "-filter_complex",
                    f"[0]bandpass=f=2000:width_type=h:w=2000,"
                    f"afade=t=in:st=0:d=0.5,afade=t=out:st={fo}:d=0.6,"
                    f"volume=1.4[wash];"
                    f"[1]volume=1.8,afade=t=in:st=0:d=0.3,"
                    f"afade=t=out:st={fo}:d=1.0[bass];"
                    f"[wash][bass]amix=inputs=2:duration=longest:normalize=0",
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "cascade_fade":
        # V6: cascade SFX strong at start, fades out as we approach hotel
        # V16: ADD low rumble (35Hz) + droplet brightness (high noise filter)
        fade_start = dur * 0.4
        fade_dur   = dur * 0.35
        return run([FFMPEG, "-y",
                    "-f", "lavfi", "-i", f"anoisesrc=d={d}:c=white:r=44100:a=0.65",
                    "-f", "lavfi", "-i", f"sine=f=45:d={d}:r=44100",
                    "-f", "lavfi", "-i", f"sine=f=30:d={d}:r=44100",   # V16: deeper rumble
                    "-f", "lavfi", "-i", f"anoisesrc=d={d}:c=pink:r=44100:a=0.30",  # V16: droplets brightness
                    "-filter_complex",
                    f"[0]bandpass=f=2000:width_type=h:w=2000,"
                    f"afade=t=in:st=0:d=0.3,"
                    f"afade=t=out:st={fade_start:.3f}:d={fade_dur:.3f},"
                    f"volume=1.6[wash];"
                    f"[1]volume=1.8,afade=t=in:st=0:d=0.2,"
                    f"afade=t=out:st={fade_start:.3f}:d={fade_dur:.3f}[bass];"
                    f"[2]volume=1.2,afade=t=in:st=0:d=0.4,"     # V16: 30Hz deep rumble
                    f"afade=t=out:st={fade_start:.3f}:d={fade_dur:.3f}[deepbass];"
                    f"[3]highpass=f=4000,volume=0.30,"          # V16: droplet sparkle
                    f"afade=t=in:st=0:d=0.5,"
                    f"afade=t=out:st={fade_start:.3f}:d={fade_dur:.3f}[drops];"
                    f"[wash][bass][deepbass][drops]amix=inputs=4:duration=longest:normalize=0",
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "birds":
        # V16: more natural — 2 tonal layers + irregular tremolo for chirps
        return run([FFMPEG, "-y",
                    "-f", "lavfi", "-i", f"sine=f=2400:d={d}:r=44100",
                    "-f", "lavfi", "-i", f"sine=f=3200:d={d}:r=44100",
                    "-filter_complex",
                    f"[0]tremolo=f=7:d=0.95,vibrato=f=5:d=0.5,bandpass=f=2600:w=2000,"
                    f"volume=0.30[a];"
                    f"[1]tremolo=f=11:d=0.85,vibrato=f=8:d=0.6,bandpass=f=3200:w=1200,"
                    f"volume=0.18[b];"
                    f"[a][b]amix=inputs=2:duration=longest:normalize=0,"
                    f"afade=t=in:st=0:d=0.6,afade=t=out:st={fo}:d=0.8",
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "lapping":
        # V16: water lapping (low-mid filtered pink noise with slow tremolo)
        lavfi = (f"anoisesrc=d={d}:c=pink:r=44100:a=0.45,"
                 f"lowpass=f=900,"
                 f"tremolo=f=0.8:d=0.6,"
                 f"afade=t=in:st=0:d=0.8,afade=t=out:st={fo}:d=1.0,"
                 f"volume=0.50")
        return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "bells":
        lavfi = (f"sine=f=600:d={d}:r=44100,"
                 f"aecho=0.7:0.4:60|120|180:0.5|0.35|0.25,"
                 f"highpass=f=400,"
                 f"afade=t=in:st=0:d=0.05,afade=t=out:st={fo}:d=1.2,"
                 f"volume=0.3")
        return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "train":
        lavfi = (f"sine=f=160:d={d}:r=44100,"
                 f"vibrato=f=0.6:d=0.4,"
                 f"lowpass=f=350,"
                 f"afade=t=in:st=0:d=0.4,afade=t=out:st={fo}:d=0.5,"
                 f"volume=0.6")
        return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "train_whistle":
        # V16: low rumble + a single distant train whistle near mid-clip
        whistle_st = max(0.5, dur * 0.55)
        return run([FFMPEG, "-y",
                    "-f", "lavfi", "-i", f"sine=f=160:d={d}:r=44100",
                    "-f", "lavfi", "-i", f"sine=f=750:d={d}:r=44100",
                    "-filter_complex",
                    f"[0]vibrato=f=0.6:d=0.4,lowpass=f=350,"
                    f"afade=t=in:st=0:d=0.4,afade=t=out:st={fo}:d=0.5,"
                    f"volume=0.55[rumble];"
                    f"[1]vibrato=f=2.5:d=0.4,bandpass=f=850:w=300,"
                    f"afade=t=in:st={whistle_st}:d=0.20,"
                    f"afade=t=out:st={whistle_st+0.7}:d=0.6,"
                    f"volume=0.35[whistle];"
                    f"[rumble][whistle]amix=inputs=2:duration=longest:normalize=0",
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "riser":
        # V16: synthesizer riser for accelerating finale — frequency ramps up
        # Use sine with frequency expression: starts low, ends high
        return run([FFMPEG, "-y",
                    "-f", "lavfi", "-i", f"sine=f=80:d={d}:r=44100",
                    "-f", "lavfi", "-i", f"anoisesrc=d={d}:c=white:r=44100:a=0.40",
                    "-filter_complex",
                    # Bass swell — slow tremolo + slight pitch lift via vibrato
                    f"[0]vibrato=f=0.3:d=0.8,"
                    f"volume='0.35+t*0.020':eval=frame,"
                    f"afade=t=out:st={fo}:d=0.8[bass];"
                    # White noise riser — bandpass sweep simulated by lowpass that opens up
                    f"[1]highpass=f=1000,"
                    f"volume='0.10+t*0.040':eval=frame,"
                    f"afade=t=out:st={fo}:d=0.6[noise];"
                    f"[bass][noise]amix=inputs=2:duration=longest:normalize=0",
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "outro_ambient":
        # V16: warm low drone bass + soft footsteps + light wind
        steps_per_sec = 1.4
        return run([FFMPEG, "-y",
                    "-f", "lavfi", "-i", f"sine=f=70:d={d}:r=44100",
                    "-f", "lavfi", "-i", f"sine=f=110:d={d}:r=44100",
                    "-f", "lavfi", "-i", f"anoisesrc=d={d}:c=brown:r=44100:a=0.4",
                    "-filter_complex",
                    f"[0]volume=0.30[bass1];"
                    f"[1]vibrato=f=0.3:d=0.4,volume=0.18[bass2];"
                    f"[2]lowpass=f=300,tremolo=f={steps_per_sec}:d=0.92,"
                    f"volume=0.55[steps];"
                    f"[bass1][bass2][steps]amix=inputs=3:duration=longest:normalize=0,"
                    f"afade=t=in:st=0:d=1.0,afade=t=out:st={fo}:d=1.5",
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "wind_global":
        # V16: subtle continuous wind layer (mixed at low volume into final)
        lavfi = (f"anoisesrc=d={d}:c=pink:r=44100:a=0.25,"
                 f"lowpass=f=600,"
                 f"tremolo=f=0.15:d=0.5,"
                 f"afade=t=in:st=0:d=3.0,afade=t=out:st={fo}:d=3.0,"
                 f"volume=0.18")
        return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "sail":
        lavfi = (f"anoisesrc=d={d}:c=pink:r=44100:a=0.25,"
                 f"bandpass=f=1100:width_type=h:w=900,"
                 f"tremolo=f=1.2:d=0.5,"
                 f"afade=t=in:st=0:d=0.5,afade=t=out:st={fo}:d=0.5,"
                 f"volume=0.5")
        return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "ambient":
        return run([FFMPEG, "-y",
                    "-f", "lavfi", "-i", f"sine=f=110:d={d}:r=44100",
                    "-f", "lavfi", "-i", f"sine=f=165:d={d}:r=44100",
                    "-filter_complex",
                    f"[0]volume=0.10[a];[1]volume=0.06[b];"
                    f"[a][b]amix=inputs=2:duration=longest:normalize=0,"
                    f"afade=t=in:st=0:d=1.0,afade=t=out:st={fo}:d=1.0",
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    if sfx_type == "footsteps":
        steps_per_sec = 1.4
        lavfi = (f"anoisesrc=d={d}:c=brown:r=44100:a=0.5,"
                 f"lowpass=f=300,"
                 f"tremolo=f={steps_per_sec}:d=0.95,"
                 f"afade=t=in:st=0:d=0.2,afade=t=out:st={fo}:d=0.3,"
                 f"volume=1.1")
        return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                    "-t", d, "-ar", "44100", "-ac", "2", out_path])

    return run([FFMPEG, "-y",
                "-f", "lavfi", "-i", f"anoisesrc=d={d}:c=white:r=44100:a=0.0",
                "-t", d, "-ar", "44100", "-ac", "2", out_path])


def render_xfade_pair(subs_a, subs_b, transition_type, duration, idx):
    """Concat sub-clips of A, concat sub-clips of B, xfade between them.
       Returns path to single transition_pair.mp4 file."""
    temp_a = f"{TMP}/trans_{idx:02d}_a.mp4"
    temp_b = f"{TMP}/trans_{idx:02d}_b.mp4"
    out_pair = f"{TMP}/trans_{idx:02d}_pair.mp4"
    if os.path.exists(out_pair) and os.path.getsize(out_pair) > 50000:
        return out_pair

    list_a = f"{TMP}/trans_{idx:02d}_a.txt"
    list_b = f"{TMP}/trans_{idx:02d}_b.txt"
    with open(list_a, "w") as f:
        for s in subs_a:
            f.write(f"file '{s}'\n")
    with open(list_b, "w") as f:
        for s in subs_b:
            f.write(f"file '{s}'\n")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_a,
         "-c:v", "copy", temp_a], tag=f"xfade-{idx}-A")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_b,
         "-c:v", "copy", temp_b], tag=f"xfade-{idx}-B")

    r = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries",
                        "format=duration", "-of", "csv=p=0", temp_a],
                       capture_output=True, text=True)
    a_dur = float(r.stdout.strip())
    offset = max(0.0, a_dur - duration)

    run([FFMPEG, "-y",
         "-i", temp_a, "-i", temp_b,
         "-filter_complex",
         f"[0:v][1:v]xfade=transition={transition_type}:duration={duration}:offset={offset:.3f}",
         "-c:v", "libx264", "-preset", PRESET_SUB, "-crf", str(CRF_SUB),
         "-r", "30", "-pix_fmt", "yuv420p", "-an",
         out_pair], tag=f"xfade-{idx}-mix")
    return out_pair


def make_sting(out_path, dur=1.6):
    """Short cinematic boom sting for act transitions."""
    fo = max(0.1, dur - 0.4)
    lavfi = (
        f"sine=f=45:d={dur:.3f}:r=44100,"
        f"volume=2.2,"
        f"afade=t=in:st=0:d=0.03,"
        f"afade=t=out:st={fo:.3f}:d={dur-fo:.3f}"
    )
    return run([FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
                "-t", f"{dur:.3f}", "-ar", "44100", "-ac", "2", out_path])


# ============================================================
# Per-clip processing
# ============================================================

def process_subseg(out_path, clip_path, ss, src_dur, speed, brightness,
                   sub_out_dur, reframe, lut_strength=LUT_STRENGTH,
                   motion_blur=False, contrast=CONTRAST, saturation=SAT_MULT,
                   src_fps=30, extra=None, gamma=1.0, exposure_fix=False):
    """V11 saccadé fix: when motion_blur=True we insert minterpolate BEFORE setpts.
       V13: when exposure_fix=True, applies S-curve + warm shift + contrast boost
       to recover mids/highlights while keeping deep blacks (for #2 lac brumeux,
       #14 rotation — overcast underexposed clips)."""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 50000:
        return
    pts = 1.0 / speed
    a_str = 1.0 - lut_strength
    b_str = lut_strength
    zs, ze = reframe
    crop_chain = build_crop_filter(zs, ze, src_dur, src_fps)
    scale_chain = "" if crop_chain else f"scale={OUT_W}:{OUT_H}:flags=lanczos,"
    # V13 4K cost cut: minterpolate fps 120 → 60 (was too slow at 4K).
    # 60fps is enough to smooth 30fps×0.85 (= 51fps effective) and 30fps×0.5 (= 30fps effective).
    interp_chain = (
        f"minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
        if motion_blur else ""
    )
    hflip_chain = "hflip," if extra == "hflip" else ""

    # V13: per-clip exposure recovery (S-curve + warm shift + contrast 1.08)
    # S-curve compresses 0-0.05 toward black (deep blacks preserved), then steep
    # lift on mids and highlights. Combined with -blue colorbalance to neutralize
    # the cold cast on overcast clips.
    if exposure_fix:
        grade_chain = (
            f"[bl]curves=master='0/0 0.05/0.02 0.20/0.27 0.50/0.62 0.80/0.88 1/1':all='0/0 1/1',"
            f"colorbalance=bs=-0.05:bm=-0.03:bh=-0.02,"
            f"eq=saturation={saturation:.3f}:gamma={gamma:.3f}:contrast=1.080,"
            f"vignette=PI/5.5[out]"
        )
    else:
        grade_chain = (
            f"[bl]eq=brightness={brightness:.4f}:contrast={contrast:.3f}:saturation={saturation:.3f}:gamma={gamma:.3f},"
            f"vignette=PI/5.5[out]"  # V13: PI/5 → PI/5.5 (slightly stronger)
        )

    fc = (
        f"[0:v]"
        f"{hflip_chain}"
        f"{scale_chain}"
        f"{crop_chain}"
        f"{interp_chain}"
        f"setpts={pts:.5f}*PTS,"
        f"split[a][b];"
        f"[b]lut3d={LUT}[lb];"
        f"[a][lb]blend=all_expr='A*{a_str:.3f}+B*{b_str:.3f}'[bl];"
        f"{grade_chain}"
    )
    # V6: FRAME-PRECISE — force exact output frame count
    out_frames = int(round(sub_out_dur * FPS))
    run([FFMPEG, "-y",
         "-ss", f"{ss:.3f}", "-t", f"{src_dur+0.5:.3f}",  # read slightly more, will be cut
         "-i", clip_path,
         "-filter_complex", fc,
         "-map", "[out]",
         "-frames:v", str(out_frames),                   # exact frame count
         "-c:v", "libx264", "-preset", PRESET_SUB, "-crf", str(CRF_SUB),
         "-r", str(FPS), "-pix_fmt", "yuv420p", "-an",
         out_path], tag="sub")


def process_clip(idx, fname, src_start, out_dur, speed, sfx_type, reframe, extra=None):
    """Process one EDIT entry → list of subseg video files + 1 SFX file."""
    clip_path = os.path.join(CLIPS, fname)
    fps = get_fps(clip_path)

    if speed == "CASCADE_SPECIAL":
        return process_cascade_special(idx, fname, src_start, out_dur, sfx_type, reframe)
    if speed == "FINALE_SPECIAL":
        return process_finale_special(idx, fname, src_start, out_dur, sfx_type, reframe, (0.5, 0.3))
    if speed == "FINALE_SPECIAL_V4":
        return process_finale_special(idx, fname, src_start, out_dur, sfx_type, reframe, (0.7, 0.5))

    if isinstance(speed, tuple):
        speed = (clamp_speed_for_fps(speed[0], fps), clamp_speed_for_fps(speed[1], fps))
    else:
        speed = clamp_speed_for_fps(speed, fps)
    subs = resolve_segments(speed, out_dur, reframe)

    luma = get_luma(clip_path, src_start, out_dur)
    # V8: brightness=0 ALWAYS, use gamma+contrast tiered by luma — preserves TRUE BLACKS
    bright = 0.0
    if luma < 85:
        gamma, contrast_clip = 1.18, 1.18
    elif luma < 100:
        gamma, contrast_clip = 1.12, 1.12
    elif luma < 110:
        gamma, contrast_clip = 1.05, 1.08
    else:
        gamma, contrast_clip = 1.0, CONTRAST

    # V12: full per-plan grade override based on signalstats analysis
    # baseline: LUT_STRENGTH=0.50, SAT_MULT=0.90
    # Goal: align all plans to a consistent natural look; reduce green/teal punch
    # on overly saturated Act 1 plans (#3-#7) and keep darks rich on Act 3.
    CLIP_GRADE = {
        # filename substring : {"lut": x, "sat": y, "gamma": z, "contrast": w, "exposure_fix": bool}
        # --- Act 0 ---
        "0102_D-00.00.00.000": {"lut": 0.50, "sat": 0.88},                # #1 chalet
        # V13: #2 underexposed (overcast lac) — S-curve + warm shift exposure_fix
        # V16: sat 0.92 → 1.20 (more punch on lake/forest greens, align with neighbors)
        "0090_D-00.00.08.762": {"lut": 0.45, "sat": 1.20, "exposure_fix": True},  # #2 lac brumeux
        # --- Act 1 (Verts vifs à calmer) ---
        "0084_D-00.00.20.048": {"lut": 0.42, "sat": 0.82},                # #3 reveal
        "0084_D-00.01.35.758": {"lut": 0.42, "sat": 0.80},                # #4 routes
        "0084_D-00.01.21.489": {"lut": 0.40, "sat": 0.78},                # #5 top-down
        "0084_D-00.03.01.139": {"lut": 0.35, "sat": 0.78},                # #6 pan reveal (outlier ++)
        "0085_D-00.00.17.296": {"lut": 0.42, "sat": 0.82},                # #7 reveal lac
        # --- Act 2 ---
        "0086_D-00.00.39.881": {"lut": 0.45, "sat": 0.85},                # #8 high overhead
        "0099_D-00.00.07.570": {"lut": 0.45, "sat": 0.85},                # #9 gare
        "0098_D-00.00.05.498": {"lut": 0.45, "sat": 0.85},                # #11 NEW pont rivière (V14)
        "0098_D-00.01.48.108": {"lut": 0.45, "sat": 0.85},                # #12 urban→cascade
        "0097_D-00.00.22.142": {"lut": 0.45, "sat": 0.85},                # #12 bât.+rivière
        # --- Act 3 (dark — keep gamma lift) ---
        "0092_D-00.00.35.454": {"lut": 0.50, "sat": 0.95, "gamma": 1.08}, # #13 cascade
        # V13: #15 rotation same underexposure as #2 — V16 sat 0.93 → 1.10 (align with #14/#16)
        "0091_D-00.00.21.529": {"lut": 0.48, "sat": 1.10, "gamma": 1.08, "exposure_fix": True},  # #15 rotation
        "0094_D-00.01.05.439": {"lut": 0.50, "sat": 0.95, "gamma": 1.08}, # #15 route→lac
        # --- Act 4 ---
        "0096_D-00.00.48.241": {"lut": 0.50, "sat": 0.95, "gamma": 1.05}, # #17 marina
        # --- Act 5 ---
        "0105_D-00.00.01.915": {"lut": 0.45, "sat": 0.88},                # #21 finale
    }
    lut_strength_clip = LUT_STRENGTH
    sat_clip          = SAT_MULT
    exposure_fix      = False
    for key, override in CLIP_GRADE.items():
        if key in fname:
            lut_strength_clip = override.get("lut", LUT_STRENGTH)
            sat_clip          = override.get("sat", SAT_MULT)
            if "gamma" in override:    gamma = override["gamma"]
            if "contrast" in override: contrast_clip = override["contrast"]
            if override.get("exposure_fix"): exposure_fix = True
            break

    speed_disp = f"{speed[0]:.2f}→{speed[1]:.2f}" if isinstance(speed, tuple) else f"{speed:.2f}"
    rf_disp = f"{reframe[0]:.2f}→{reframe[1]:.2f}" if reframe else "static"
    extra_disp = f"  extra={extra}" if extra else ""
    print(f"\n[{idx+1:02d}/{len(EDIT)}] {fname[:54]}")
    print(f"      fps={fps:.1f}  speed={speed_disp}  out={out_dur:.1f}s  "
          f"subs={len(subs)}  luma={luma:.0f}  bright={bright:+.3f}  gamma={gamma:.2f}  "
          f"sfx={sfx_type}  reframe={rf_disp}{extra_disp}")

    src_fps_int = 60 if fps >= 50 else 30
    sub_videos = []
    cur_offset = 0.0
    for j, (sub_src, sub_speed, sub_out, sub_rf) in enumerate(subs):
        out = f"{TMP}/clip_{idx:02d}_{j}.mp4"
        # V11: enable motion-compensated frame interpolation when
        # 30fps source is slowed below 0.9x (effective <27fps = saccadé).
        eff_speed = sub_speed
        need_interp = (src_fps_int < 50 and eff_speed < 0.9)
        process_subseg(out, clip_path, src_start + cur_offset,
                       sub_src, sub_speed, bright, sub_out, sub_rf,
                       src_fps=src_fps_int, extra=extra, gamma=gamma,
                       contrast=contrast_clip, lut_strength=lut_strength_clip,
                       saturation=sat_clip, motion_blur=need_interp,
                       exposure_fix=exposure_fix)
        sub_videos.append(out)
        cur_offset += sub_src

    sfx_out = f"{TMP}/sfx_{idx:02d}.aac"
    make_sfx(sfx_type, out_dur, sfx_out)

    return sub_videos, sfx_out, out_dur


def process_cascade_special(idx, fname, src_start, out_dur, sfx_type, reframe):
    """V4 Cascade: 0.3s freeze + 7.2s ramp 0.4→0.2 + 10.5s hold 0.2x.
       Reframe: 1.0 → 1.15 (bigger push than V3).
       Push peak lands on music peak 91.5s."""
    clip_path = os.path.join(CLIPS, fname)
    fps = get_fps(clip_path)
    luma = get_luma(clip_path, src_start, out_dur)
    bright = (0.12 if luma < 85 else 0.07 if luma < 95 else 0.0)

    print(f"\n[{idx+1:02d}/{len(EDIT)}] CASCADE SPECIAL {fname[:42]}")
    print(f"      luma={luma:.0f} bright={bright:+.3f} sfx={sfx_type}")

    # V4 cascade timing: out_dur=18s = freeze(0.3) + ramp(7.2) + hold(10.5)
    FREEZE_DUR = 0.3
    RAMP_DUR = 7.2
    HOLD_DUR = out_dur - FREEZE_DUR - RAMP_DUR  # = 10.5

    src_fps_int = 60 if fps >= 50 else 30
    zs, ze = reframe if reframe else (1.0, 1.15)
    # Push reaches max at end of ramp (= music peak 91.5)
    rz_mid = ze

    # Segment plan:
    # SEG A: 0.3s freeze (clone 1st frame)
    # SEG B: 8.5s ramp 0.4→0.2 (linear), zoom zs → rz_mid (= ze actually)
    # SEG C: 5.2s constant 0.2x, zoom rz_mid → ze (very slight push)

    a_str = 1.0 - LUT_STRENGTH
    b_str = LUT_STRENGTH

    # --- SEG A: freeze frame 0.3s ---
    # Extract a single PNG at src_start, then use it as a looped input.
    freeze_png = f"{TMP}/clip_{idx:02d}_freeze.png"
    if not os.path.exists(freeze_png):
        run([FFMPEG, "-y",
             "-ss", f"{src_start:.3f}",
             "-i", clip_path,
             "-frames:v", "1",
             freeze_png], tag="extract-freeze-png")

    segA = f"{TMP}/clip_{idx:02d}_A.mp4"
    if not os.path.exists(segA) or os.path.getsize(segA) < 50000:
        crop_a = build_crop_filter(zs, zs, 0.3)
        scale_a = "" if crop_a else f"scale={OUT_W}:{OUT_H}:flags=lanczos,"
        fc_A = (
            f"[0:v]"
            f"{scale_a}"
            f"{crop_a}"
            f"split[a][b];[b]lut3d={LUT}[lb];"
            f"[a][lb]blend=all_expr='A*{a_str:.3f}+B*{b_str:.3f}'[bl];"
            f"[bl]eq=brightness={bright:.4f}:contrast=1.10:saturation=1.05,vignette=PI/5.5[out]"
        )
        run([FFMPEG, "-y",
             "-loop", "1", "-t", "0.3", "-r", "30",
             "-i", freeze_png,
             "-filter_complex", fc_A,
             "-map", "[out]",
             "-c:v", "libx264", "-preset", PRESET_SUB, "-crf", str(CRF_SUB),
             "-r", "30", "-pix_fmt", "yuv420p", "-an",
             segA], tag="sub-A-freeze")

    # --- SEG B: RAMP_DUR ramp 0.4→0.2 (V4: 7.2s) ---
    sub_videos = [segA]
    cur_off = 0.0
    subs_B = resolve_segments((0.4, 0.2), RAMP_DUR, (zs, rz_mid))
    for k, (sub_src, sub_speed, sub_out, sub_rf) in enumerate(subs_B):
        out = f"{TMP}/clip_{idx:02d}_B{k}.mp4"
        process_subseg(out, clip_path, src_start + cur_off,
                       sub_src, sub_speed, bright, sub_out, sub_rf,
                       src_fps=src_fps_int)
        sub_videos.append(out)
        cur_off += sub_src

    # --- SEG C: HOLD_DUR constant 0.2x (V4: 10.5s, zoom held at ze=1.15) ---
    segC = f"{TMP}/clip_{idx:02d}_C.mp4"
    src_C = HOLD_DUR * 0.2
    process_subseg(segC, clip_path, src_start + cur_off,
                   src_C, 0.2, bright, HOLD_DUR, (rz_mid, ze),
                   src_fps=src_fps_int)
    sub_videos.append(segC)

    sfx_out = f"{TMP}/sfx_{idx:02d}.aac"
    make_sfx(sfx_type, out_dur, sfx_out)
    return sub_videos, sfx_out, out_dur


def process_finale_special(idx, fname, src_start, out_dur, sfx_type, reframe,
                           ramp=(0.5, 0.3)):
    """Finale: 8.5s ramp s1→s2 + 5.5s hold s2x."""
    clip_path = os.path.join(CLIPS, fname)
    fps = get_fps(clip_path)
    luma = get_luma(clip_path, src_start, out_dur)
    bright = (0.12 if luma < 85 else 0.07 if luma < 95 else 0.0)

    s1, s2 = ramp
    print(f"\n[{idx+1:02d}/{len(EDIT)}] FINALE SPECIAL {fname[:38]} ramp {s1}→{s2}+hold")
    print(f"      luma={luma:.0f} bright={bright:+.3f}")

    src_fps_int = 60 if fps >= 50 else 30
    zs, ze = reframe if reframe else (1.0, 1.0)
    rz_mid = zs + (ze - zs) * (8.5 / 14.0)

    sub_videos = []
    cur_off = 0.0

    subs = resolve_segments(ramp, 8.5, (zs, rz_mid))
    for k, (sub_src, sub_speed, sub_out, sub_rf) in enumerate(subs):
        out = f"{TMP}/clip_{idx:02d}_R{k}.mp4"
        process_subseg(out, clip_path, src_start + cur_off,
                       sub_src, sub_speed, bright, sub_out, sub_rf,
                       src_fps=src_fps_int)
        sub_videos.append(out)
        cur_off += sub_src

    out_hold = f"{TMP}/clip_{idx:02d}_H.mp4"
    src_hold = 5.5 * s2
    process_subseg(out_hold, clip_path, src_start + cur_off,
                   src_hold, s2, bright, 5.5, (rz_mid, ze),
                   src_fps=src_fps_int)
    sub_videos.append(out_hold)

    sfx_out = f"{TMP}/sfx_{idx:02d}.aac"
    make_sfx(sfx_type, out_dur, sfx_out)
    return sub_videos, sfx_out, out_dur


def process_outro():
    """Render outro [32] with MERCI overlay baked in."""
    fname, src_start, out_dur, speed, sfx_type, reframe = OUTRO
    clip_path = os.path.join(CLIPS, fname)
    fps = get_fps(clip_path)
    src_fps_int = 60 if fps >= 50 else 30
    pts = 1.0 / speed
    luma = get_luma(clip_path, src_start, out_dur)
    # V9 fix: brightness=0, gamma+contrast for neutral with deep blacks
    bright = 0.0
    if luma < 85:
        outro_gamma, outro_contrast = 1.10, 1.15
    else:
        outro_gamma, outro_contrast = 1.04, 1.10

    print(f"\n--- OUTRO ---")
    print(f"  {fname[:50]} src={src_start} out={out_dur} speed={speed} luma={luma:.0f} γ={outro_gamma} c={outro_contrast}")

    # LUT at 50% for skin-friendly
    a_str, b_str = 0.50, 0.50
    # V11: stagger MERCI then "À bientôt"
    main_in_st  = 0.6
    main_out_st = out_dur - 1.3
    sub_in_st   = 1.8     # appears ~1.2s after MERCI
    sub_out_st  = out_dur - 1.3
    crop_chain = build_crop_filter(reframe[0], reframe[1], out_dur * speed, src_fps_int)
    scale_chain = "" if crop_chain else f"scale={OUT_W}:{OUT_H}:flags=lanczos,"

    # Read PNG dims for right-alignment
    from PIL import Image as _PI
    pm = _PI.open(OUTRO_MAIN_PNG); main_pw, main_ph = pm.size; pm.close()
    ps = _PI.open(OUTRO_SUB_PNG);  sub_pw,  sub_ph  = ps.size; ps.close()
    right_edge_x = int(OUT_W * 0.90)
    # MERCI anchored bottom-right zone (V6: y=0.82)
    main_x = right_edge_x - main_pw
    main_y = int(OUT_H * 0.78) - main_ph // 2
    # V12: TIGHT spacing between THANK YOU and "See you soon" (S(50) → S(15))
    # V13: fade only — no vertical slide
    sub_x_final = right_edge_x - sub_pw
    sub_y       = main_y + main_ph + S(15)

    fc = (
        f"[0:v]"
        f"{scale_chain}"
        f"{crop_chain}"
        f"setpts={pts:.5f}*PTS,"
        f"split[a][b];[b]lut3d={LUT}[lb];"
        f"[a][lb]blend=all_expr='A*{a_str:.2f}+B*{b_str:.2f}'[bl];"
        f"[bl]eq=brightness={bright:.4f}:contrast={outro_contrast}:saturation=1.05:gamma={outro_gamma},vignette=PI/5.5[graded];"
        f"[1:v]format=rgba,"
        f"fade=t=in:st={main_in_st}:d=0.7:alpha=1,"
        f"fade=t=out:st={main_out_st}:d=0.7:alpha=1[main_f];"
        f"[2:v]format=rgba,"
        f"fade=t=in:st={sub_in_st}:d=0.6:alpha=1,"   # V13: pure alpha fade (no slide)
        f"fade=t=out:st={sub_out_st}:d=0.7:alpha=1[sub_f];"
        f"[graded][main_f]overlay={main_x}:{main_y}:format=auto[g2];"
        f"[g2][sub_f]overlay={sub_x_final}:{sub_y}:format=auto[out]"
    )

    vout = f"{TMP}/outro_v.mp4"
    run([FFMPEG, "-y",
         "-ss", f"{src_start:.3f}", "-t", f"{out_dur*speed:.3f}",
         "-i", clip_path,
         "-loop", "1", "-t", f"{out_dur:.3f}",
         "-i", OUTRO_MAIN_PNG,
         "-loop", "1", "-t", f"{out_dur:.3f}",
         "-i", OUTRO_SUB_PNG,
         "-filter_complex", fc,
         "-map", "[out]",
         "-c:v", "libx264", "-preset", PRESET_FINAL, "-crf", str(CRF_FINAL),
         "-r", "30", "-pix_fmt", "yuv420p", "-an",
         vout], tag="outro-v")

    aout = f"{TMP}/outro_a.aac"
    make_sfx(sfx_type, out_dur, aout)
    return vout, aout, out_dur


def process_end_credits():
    """V9: 9s with PARKING clip background (top-down) + credits PNG overlay.
       Parking src=8 (end of clip), 6s of source slowed to 9s output (0.67x)."""
    dur = 9.0
    vout = f"{TMP}/credits_v.mp4"
    parking_src = os.path.join(CLIPS, "DJI_20260516153528_0105_D-00.01.08.703-00.01.22.165-seg2.MP4")
    src_start  = 8.0
    src_dur    = 6.0      # 6s of source → 9s output via setpts*1.5
    pts_factor = dur / src_dur   # 1.5

    # Background: parking with LUT + darkening + vignette, then black overlay 45%, then credits
    fc = (
        f"[0:v]scale={OUT_W}:{OUT_H}:flags=lanczos,"
        f"setpts={pts_factor:.4f}*PTS,"
        f"lut3d={LUT},"
        f"eq=brightness=-0.05:contrast=1.15:saturation=1.05:gamma=0.95,"
        f"vignette=PI/4[bg];"
        f"color=c=black@0.45:s={OUT_W}x{OUT_H}:d={dur}:r={FPS}[blk];"
        f"[bg][blk]overlay=0:0[base];"
        f"[2:v]format=rgba,"
        f"fade=t=in:st=1.0:d=1.2:alpha=1,"
        f"fade=t=out:st={dur-1.5}:d=1.5:alpha=1[c];"
        f"[base][c]overlay=0:0[out]"
    )
    run([FFMPEG, "-y",
         "-ss", str(src_start), "-t", str(src_dur), "-i", parking_src,
         "-f", "lavfi", "-i", f"color=c=black:s={OUT_W}x{OUT_H}:d={dur}:r={FPS}",
         "-loop", "1", "-t", f"{dur}", "-i", CREDITS_PNG,
         "-filter_complex", fc,
         "-map", "[out]",
         "-frames:v", str(int(dur*FPS)),
         "-c:v", "libx264", "-preset", PRESET_FINAL, "-crf", str(CRF_FINAL+1),
         "-r", str(FPS), "-pix_fmt", "yuv420p",
         vout], tag="credits-v")
    return vout, dur


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print(f"  Interlaken V3 — {OUT_W}x{OUT_H} [{QUALITY}]")
    print("=" * 60)

    os.makedirs(TMP, exist_ok=True)
    if not os.path.exists(LUT):
        shutil.copy2(LUT_SRC, LUT)
    print(f"LUT  → {LUT}\n")

    # 1) Generate PNG overlays
    print("--- Generating PNGs ---")
    generate_title_png()
    generate_outro_png()
    generate_credits_png()

    # 2) Process main clips (track sub-segments per clip for transitions)
    clip_subs_list = []   # list of (clip_idx, [sub_paths], duration)
    all_sfxs = []
    out_durs = []
    for idx, entry in enumerate(EDIT):
        subs, sfx, dur = process_clip(idx, *entry)
        clip_subs_list.append((idx, subs, dur))
        all_sfxs.append(sfx)
        out_durs.append(dur)

    # === V14: TRANSITIONS — indices shifted +1 after inserting #11 NEW 0098-seg1 ===
    TRANSITIONS = [
        (13, 14, "circleopen", 0.5, "wind"),     # cascade → rotation
        (20, 21, "fadeblack",  0.4, "boom"),     # château → finale
    ]
    transition_starts = {t[0]: t for t in TRANSITIONS}

    # Render xfade pairs for transition points
    final_subs = []
    transition_events = []  # (output_time, sfx_type, duration) for audio
    cumulative_time = 0.0
    i = 0
    while i < len(clip_subs_list):
        cur_idx, cur_subs, cur_dur = clip_subs_list[i]
        if cur_idx in transition_starts and i + 1 < len(clip_subs_list):
            a_idx, b_idx, ttype, tdur, tsfx = transition_starts[cur_idx]
            next_idx, next_subs, next_dur = clip_subs_list[i+1]
            pair_file = render_xfade_pair(cur_subs, next_subs, ttype, tdur, cur_idx)
            final_subs.append(pair_file)
            # Transition midpoint in output timeline
            trans_mid = cumulative_time + cur_dur - tdur/2
            transition_events.append((trans_mid, tsfx, tdur))
            # Output duration = cur_dur + next_dur - tdur
            cumulative_time += cur_dur + next_dur - tdur
            i += 2
        else:
            final_subs.extend(cur_subs)
            cumulative_time += cur_dur
            i += 1

    main_dur = cumulative_time
    print(f"\n✓ Main montage duration (with {len(transition_events)} transitions): {main_dur:.2f}s ({main_dur/60:.2f} min)")
    for ev in transition_events:
        print(f"  transition: t={ev[0]:.2f}s sfx={ev[1]} dur={ev[2]:.2f}s")

    # 3) Process outro
    outro_v, outro_a, outro_dur = process_outro()
    print(f"✓ Outro duration: {outro_dur:.2f}s")

    # 4) Process end credits
    credits_v, credits_dur = process_end_credits()
    print(f"✓ End credits duration: {credits_dur:.2f}s")

    # 5) Concat main video (using final_subs which has transition pairs)
    print("\n--- Concat main video ---")
    cf = f"{TMP}/main_video_list.txt"
    with open(cf, "w") as f:
        for v in final_subs:
            f.write(f"file '{v}'\n")
    main_video = f"{TMP}/main_video.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", cf,
         "-c:v", "copy", main_video], tag="concat-v")

    # 6) Concat main SFX
    print("--- Concat main SFX ---")
    sf = f"{TMP}/main_sfx_list.txt"
    with open(sf, "w") as f:
        for s in all_sfxs:
            f.write(f"file '{s}'\n")
    main_sfx = f"{TMP}/main_sfx.aac"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", sf,
         "-c:a", "aac", "-ar", "44100", "-ac", "2", main_sfx], tag="concat-sfx")

    # 7) Generate stings audio (one boom per act transition, mixed with proper delay)
    print("--- Generate act-transition stings ---")
    sting_file = f"{TMP}/sting.aac"
    make_sting(sting_file, 1.6)

    # V16: generate wind global (continuous subtle wind for cohesion)
    # and match-cut whoosh between #10 rails and #11 NEW pont
    print("--- Generate V16 SFX layers (wind global + match cut whoosh) ---")

    # 7b) Apply title overlay to main_video (separate pass for reliability)
    print("\n--- Apply title overlay to main_video (V11: 2 PNGs, staggered) ---")
    # title appears during clip #2 (lac brumeux) which is 4-12s
    title_offset = 4.0
    title_clip_dur = 8.0
    # MAIN: fade-in at +1.0s, fade-out near end
    main_in_st  = title_offset + 1.0
    main_out_st = title_offset + title_clip_dur - 1.8
    # SUB: appears ~1.2s AFTER main, slide-in from right with alpha fade
    sub_in_st   = title_offset + 2.2
    sub_out_st  = title_offset + title_clip_dur - 1.8

    # Positions (V11: more vertical space between MAIN and SUB).
    # Read PNG dimensions to right-align both
    from PIL import Image as _PI
    pm = _PI.open(TITLE_MAIN_PNG); main_pw, main_ph = pm.size; pm.close()
    ps = _PI.open(TITLE_SUB_PNG);  sub_pw,  sub_ph  = ps.size; ps.close()

    right_edge_x = int(OUT_W * 0.92)
    main_x = right_edge_x - main_pw
    main_y = int(OUT_H * 0.65) - main_ph // 2  # V12: 0.55 → 0.65 (10% lower)
    # Sub sits below main with TIGHT spacing (V12: S(40) → S(15))
    # V13: fade only — no horizontal slide
    sub_x_final = right_edge_x - sub_pw
    sub_y       = main_y + main_ph + S(15)

    main_titled = f"{TMP}/main_titled.mp4"
    main_actual_dur = float(subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", main_video], capture_output=True, text=True
    ).stdout.strip())
    # V11: also fade-in from black on first ~1.2s of main_video here
    run([FFMPEG, "-y",
         "-i", main_video,
         "-loop", "1", "-t", f"{main_actual_dur}", "-i", TITLE_MAIN_PNG,
         "-loop", "1", "-t", f"{main_actual_dur}", "-i", TITLE_SUB_PNG,
         "-filter_complex",
         # MAIN: simple alpha fade in/out
         f"[1:v]format=rgba,"
         f"fade=t=in:st={main_in_st}:d=0.7:alpha=1,"
         f"fade=t=out:st={main_out_st}:d=0.7:alpha=1[main_f];"
         # V13: SUB pure alpha fade (no slide)
         f"[2:v]format=rgba,"
         f"fade=t=in:st={sub_in_st}:d=0.6:alpha=1,"
         f"fade=t=out:st={sub_out_st}:d=0.7:alpha=1[sub_f];"
         # V11: opening fade-in from black on first 1.2s
         f"[0:v]fade=t=in:st=0:d=1.2:color=black[v0];"
         f"[v0][main_f]overlay=x={main_x}:y={main_y}:"
         f"enable='between(t,{title_offset},{title_offset+title_clip_dur})'[v1];"
         f"[v1][sub_f]overlay=x={sub_x_final}:y={sub_y}:"
         f"enable='between(t,{title_offset},{title_offset+title_clip_dur})'[out]",
         "-map", "[out]",
         "-c:v", "libx264", "-preset", PRESET_SUB, "-crf", str(CRF_SUB),
         "-pix_fmt", "yuv420p", "-an",
         "-t", f"{main_actual_dur}",
         main_titled], tag="title-overlay")

    # 7c) Concat main_titled + outro + credits via concat DEMUXER (reliable)
    print("--- Concat full video ---")
    full_list = f"{TMP}/full_list.txt"
    with open(full_list, "w") as f:
        f.write(f"file '{main_titled}'\n")
        f.write(f"file '{TMP}/outro_v.mp4'\n")
        f.write(f"file '{TMP}/credits_v.mp4'\n")
    full_video = f"{TMP}/full_video.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", full_list,
         "-c:v", "copy", full_video], tag="concat-full")

    # 8) Final encode: grain + audio mix (V4: NO letterbox)
    print("\n--- Final encode (grain + audio, no letterbox) ---")
    total_main = main_dur + outro_dur
    total_full = total_main + credits_dur
    # V4: longer music fade-out (5s instead of 2.5s) → less abrupt
    music_fade_out_st = main_dur - 4.0
    sting_delays_ms = [int(t * 1000) - 800 for t in ACT_TRANSITIONS]

    # V16: generate wind global + match_whoosh files now (need total_full)
    wind_global_file = f"{TMP}/wind_global.aac"
    make_sfx("wind_global", total_full, wind_global_file)
    match_whoosh_file = f"{TMP}/match_whoosh.aac"
    make_sfx("whoosh", 0.6, match_whoosh_file)
    # cut time = sum of #1..#10 output durations (V16: 4+8+6+5+4+4+6+6+6+5 = 54s)
    match_cut_t = sum(e[2] for e in EDIT[:10])
    print(f"  wind_global → {wind_global_file} ({total_full:.1f}s)")
    print(f"  match_whoosh → t={match_cut_t:.1f}s ({match_whoosh_file})")

    # V4: no letterbox bars
    letterbox_chain = ""
    if LETTERBOX > 0:
        letterbox_chain = (
            f"drawbox=x=0:y=0:w=iw:h={LETTERBOX}:color=black:t=fill,"
            f"drawbox=x=0:y=ih-{LETTERBOX}:w=iw:h={LETTERBOX}:color=black:t=fill,"
        )
    vfilter = (
        f"[0:v]"
        f"{letterbox_chain}"
        f"noise=alls={GRAIN_STRENGTH}:allf=u,"  # V11: removed 't' temporal flag (anti-scintillement)
        f"fade=t=out:st={total_full-1.0}:d=1.0:color=black[vout]"
    )

    # === V5: Generate transition SFX (whoosh/wind/boom at transition points) ===
    transition_sfx_files = []
    for k, (t_time, sfx_type, t_dur) in enumerate(transition_events):
        sfx_path = f"{TMP}/transfx_{k}.aac"
        # extend duration slightly for the swoosh tail
        make_sfx(sfx_type if sfx_type != "wind" else "whoosh", t_dur + 0.3, sfx_path)
        transition_sfx_files.append((sfx_path, t_time, sfx_type))

    # Audio inputs: 0=video, 1=music, 2=main_sfx, 3=outro_sfx, 4=sting, 5+=transition_sfx files
    # Build sting chain (act transitions)
    sting_chain = ""
    if sting_delays_ms:
        sting_filters = [f"[4:a]adelay={d}|{d},volume=0.55[st{i}]"
                         for i, d in enumerate(sting_delays_ms)]
        sting_chain = ";" + ";".join(sting_filters)
        sting_mix = "".join(f"[st{i}]" for i in range(len(sting_delays_ms)))
        sting_chain += f";{sting_mix}amix=inputs={len(sting_delays_ms)}:duration=longest:normalize=0[stings]"
    else:
        sting_chain = ""

    # Build transition SFX chain
    transfx_chain = ""
    if transition_sfx_files:
        # Inputs start at index 5
        trans_filters = []
        for k, (_, t_time, _) in enumerate(transition_sfx_files):
            delay_ms = int(max(0, t_time - 0.2) * 1000)  # start sfx 0.2s before transition mid
            trans_filters.append(f"[{5+k}:a]adelay={delay_ms}|{delay_ms},volume=0.7[tx{k}]")
        transfx_chain = ";" + ";".join(trans_filters)
        tx_mix = "".join(f"[tx{k}]" for k in range(len(transition_sfx_files)))
        transfx_chain += f";{tx_mix}amix=inputs={len(transition_sfx_files)}:duration=longest:normalize=0[transfx]"

    # V16: indices: 0=video, 1=music, 2=main_sfx, 3=outro_sfx, 4=sting,
    #               then transition_sfx[5..5+N), then wind_global, then match_whoosh
    n_transfx = len(transition_sfx_files)
    wind_idx     = 5 + n_transfx
    match_idx    = 5 + n_transfx + 1

    # Wind global chain — very subtle, mix into base
    wind_chain = f";[{wind_idx}:a]volume=0.65[wind]"
    # Match whoosh — adelay to match_cut_t (peak ~0.3s into the SFX)
    mw_delay_ms = int(max(0, match_cut_t - 0.3) * 1000)
    match_chain = f";[{match_idx}:a]adelay={mw_delay_ms}|{mw_delay_ms},volume=0.55[matchwh]"

    # Final audio assembly
    extra_inputs_mix = ["[wind]", "[matchwh]"]
    if sting_chain:
        extra_inputs_mix.append("[stings]")
    if transfx_chain:
        extra_inputs_mix.append("[transfx]")

    final_mix = (
        f";[base]{(''.join(extra_inputs_mix))}amix=inputs={1+len(extra_inputs_mix)}:duration=longest:normalize=0,"
        f"apad=whole_dur={total_full},"
        f"afade=t=out:st={total_full-1.0}:d=1.0[aout]"
    )

    afilter = (
        f"[1:a]afade=t=in:st=0:d=2.5,"
        f"afade=t=out:st={music_fade_out_st:.2f}:d=10.0,"   # V5: 10s fade-out
        f"volume=0.85[mus];"
        f"[2:a]volume=0.28[main_sfx_v];"
        f"[3:a]volume=0.55,adelay={int(main_dur*1000)}|{int(main_dur*1000)}[outro_sfx_v];"
        f"[mus][main_sfx_v][outro_sfx_v]amix=inputs=3:duration=longest:normalize=0[base]"
        + sting_chain
        + transfx_chain
        + wind_chain
        + match_chain
        + final_mix
    )

    # Build input args (order MUST match indices used above)
    input_args = ["-i", full_video, "-i", MUSIC, "-i", main_sfx, "-i", outro_a, "-i", sting_file]
    for sfx_path, _, _ in transition_sfx_files:
        input_args += ["-i", sfx_path]
    # V16 additions:
    input_args += ["-i", wind_global_file, "-i", match_whoosh_file]

    run([FFMPEG, "-y", *input_args,
         "-filter_complex", f"{vfilter};{afilter}",
         "-map", "[vout]",
         "-map", "[aout]",
         "-c:v", "libx264", "-preset", PRESET_FINAL, "-crf", str(CRF_FINAL),
         "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart",
         "-t", f"{total_full:.3f}",
         OUTPUT], tag="final")

    sz_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"  ✓ V3 [{QUALITY}]:  {OUTPUT}")
    print(f"    {OUT_W}x{OUT_H}  |  {total_full:.1f}s ({total_full/60:.2f} min)  |  {sz_mb:.0f} MB")
    print(f"    Letterbox 2.35:1 + grain + LUT 80% + sync musicale niveau note")
    if QUALITY == "preview":
        print(f"    → preview only. For final 4K: QUALITY=final python3 interlaken_v3.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
