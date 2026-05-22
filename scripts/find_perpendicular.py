#!/usr/bin/env python3
"""
Find frames where the dominant linear structure (rails, road, bridge, etc.)
is closest to a target angle (default: vertical 90°).

Useful for setting up form match cuts where two adjacent shots share
the same line orientation.

Usage:
    python3 find_perpendicular.py clip.MP4 t_start t_end [target_angle]
"""
import cv2, numpy as np, subprocess, os, sys, tempfile

FFMPEG = "/opt/homebrew/bin/ffmpeg"

def extract_frame(clip, t, size=1280):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        dst = f.name
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-ss", f"{t}", "-i", clip,
                    "-vframes", "1", "-vf", f"scale={size}:-1", dst], check=True)
    return dst

def dominant_angle(img_path):
    """Returns dominant line angle (degrees, 0=horizontal, 90=vertical)."""
    img = cv2.imread(img_path)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150)
    lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180,
                            threshold=120, minLineLength=80, maxLineGap=20)
    if lines is None: return None
    angles, lengths = [], []
    for l in lines:
        x1, y1, x2, y2 = l[0]
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0: continue
        a = np.degrees(np.arctan2(dy, dx))
        if a < 0: a += 180
        angles.append(a)
        lengths.append(np.sqrt(dx*dx + dy*dy))
    if not angles: return None
    bins = np.arange(0, 180, 5)
    hist, _ = np.histogram(angles, bins=bins, weights=lengths)
    return float(bins[np.argmax(hist)] + 2.5)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: find_perpendicular.py clip.MP4 t_start t_end [target_angle=90]")
        sys.exit(1)
    clip = sys.argv[1]
    t0 = float(sys.argv[2])
    t1 = float(sys.argv[3])
    target = float(sys.argv[4]) if len(sys.argv) > 4 else 90.0

    times = np.arange(t0, t1 + 0.01, 0.2)
    print(f"Clip: {os.path.basename(clip)}")
    print(f"  Target angle: {target}°  (90° = vertical, 0° = horizontal)")
    print()
    print(f"{'t (s)':>6} {'angle':>8} {'|delta|':>9}")
    print("-" * 30)

    best = (999, None)
    for t in times:
        path = extract_frame(clip, t)
        a = dominant_angle(path)
        os.unlink(path)
        if a is None:
            continue
        # Angles are mod 180 — diff is min of |a-t| and 180-|a-t|
        delta = abs(a - target)
        if delta > 90: delta = 180 - delta
        marker = " ★" if delta < best[0] else ""
        if delta < best[0]:
            best = (delta, t)
        print(f"{t:6.1f} {a:8.1f}° {delta:8.1f}°{marker}")

    if best[1] is not None:
        print()
        print(f"★ Best frame: src={best[1]:.1f}s  (Δ={best[0]:.1f}° from target)")
    else:
        print()
        print("No dominant lines detected in the window.")
