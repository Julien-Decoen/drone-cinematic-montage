#!/usr/bin/env python3
"""
Analyze saturation / chrominance / luma of plans in a rendered preview.

Usage:
    python3 analyze_sat.py path/to/preview.mp4 t1 t2 t3 ...

Outputs a table comparing each timestamp's YAVG / UAVG_dev / VAVG_dev / SATAVG
so you can spot outliers and tune CLIP_GRADE.
"""
import subprocess, re, sys

FFMPEG = "/opt/homebrew/bin/ffmpeg"

def analyze(video, t):
    cmd = [FFMPEG, "-hide_banner", "-ss", str(t), "-t", "1.0", "-i", video,
           "-vf", "scale=640:-1,signalstats,metadata=print",
           "-an", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    e = r.stderr
    sat = [float(m) for m in re.findall(r"SATAVG=([\d.]+)", e)]
    y   = [float(m) for m in re.findall(r"YAVG=([\d.]+)", e)]
    u   = [float(m) for m in re.findall(r"UAVG=([\d.]+)", e)]
    v   = [float(m) for m in re.findall(r"VAVG=([\d.]+)", e)]
    avg = lambda xs: sum(xs)/len(xs) if xs else 0
    return avg(y), avg(u)-128, avg(v)-128, avg(sat)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: analyze_sat.py video.mp4 t1 [t2 t3 ...]")
        sys.exit(1)
    video = sys.argv[1]
    times = [float(t) for t in sys.argv[2:]]
    print(f"{'t (s)':>8} {'Y':>5} {'U_dev':>7} {'V_dev':>7} {'SAT':>6}")
    print("-" * 45)
    for t in times:
        y, u, v, s = analyze(video, t)
        print(f"{t:8.1f} {y:5.0f} {u:+7.1f} {v:+7.1f} {s:6.1f}")
