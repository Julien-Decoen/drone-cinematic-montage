#!/usr/bin/env python3
"""
Measure drone yaw rotation rate (degrees/sec) in a source clip using
ORB feature matching + RANSAC affine estimation.

Usage:
    python3 analyze_rotation.py clip.MP4 t_start t_end [step]

Outputs the mean rotation rate over the window. Use to match rotation
between two clips for form match cuts (see docs/match-cuts.md).
"""
import cv2, numpy as np, subprocess, os, sys, tempfile

FFMPEG = "/opt/homebrew/bin/ffmpeg"

def extract_frame(clip, t, size=640):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        dst = f.name
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-ss", f"{t}", "-i", clip,
                    "-vframes", "1", "-vf", f"scale={size}:-1", dst], check=True)
    img = cv2.imread(dst, cv2.IMREAD_GRAYSCALE)
    os.unlink(dst)
    return img

def rotation_between(im_a, im_b):
    """Returns degrees of rotation from a to b, or None if no match."""
    orb = cv2.ORB_create(nfeatures=2000)
    kp1, des1 = orb.detectAndCompute(im_a, None)
    kp2, des2 = orb.detectAndCompute(im_b, None)
    if des1 is None or des2 is None: return None
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    if len(matches) < 10: return None
    matches = sorted(matches, key=lambda m: m.distance)[:200]
    pts1 = np.float32([kp1[m.queryIdx].pt for m in matches])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in matches])
    M, _ = cv2.estimateAffinePartial2D(pts1, pts2, method=cv2.RANSAC)
    if M is None: return None
    angle = np.degrees(np.arctan2(M[1, 0], M[0, 0]))
    return angle

def measure_rate(clip, t0, t1, step=0.5):
    angles = []
    prev = extract_frame(clip, t0)
    t = t0
    while t + step <= t1:
        cur = extract_frame(clip, t + step)
        a = rotation_between(prev, cur)
        if a is not None:
            angles.append(a / step)   # degrees per second
        prev = cur
        t += step
    if not angles: return None, 0
    return float(np.mean(angles)), len(angles)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: analyze_rotation.py clip.MP4 t_start t_end [step]")
        sys.exit(1)
    clip = sys.argv[1]
    t0 = float(sys.argv[2])
    t1 = float(sys.argv[3])
    step = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5

    rate, n = measure_rate(clip, t0, t1, step)
    if rate is None:
        print("No rotation detected.")
        sys.exit(0)

    print(f"Clip: {os.path.basename(clip)}")
    print(f"  Window: {t0:.1f}s → {t1:.1f}s  (step {step}s, n={n} samples)")
    print(f"  Mean rotation: {rate:+.2f} °/s  ({abs(rate):.2f} °/s absolute)")
    print()
    print(f"  To match this with another clip B (natural rate r_B):")
    print(f"    target = mean(|r_A|, |r_B|)")
    print(f"    speed_A = target / |r_A|")
    print(f"    speed_B = target / |r_B|")
