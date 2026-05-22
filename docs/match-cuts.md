# Form Match Cuts

Cinematic cuts where two adjacent shots share visual line orientation or motion direction. Creates the perceptual feeling that the camera "continues" across the cut.

Two flavors covered here:

1. **Perpendicular alignment** — both shots have a dominant linear structure at the same angle (e.g. both vertical)
2. **Rotation matching** — both shots have similar drone yaw rotation rate (smooth panning continuity)

---

## 1. Perpendicular alignment

Use case: drone train rails (top-down) → drone bridge over river (top-down). Both feature linear structures. If the cut frames have those structures at the same orientation (e.g. both vertical), the eye reads continuity.

### Detection — visual + Hough

**Step 1**: Extract frames every 0.2-0.3s in the candidate window of each clip.

```python
TIMES = np.arange(8.0, 13.0, 0.2)  # e.g. for clip exit
for t in TIMES:
    subprocess.run([FFMPEG, "-y", "-ss", str(t), "-i", clip,
                    "-vframes","1","-vf",f"scale=1280:720", f"{OUT}/f_{t:.1f}.png"])
```

**Step 2**: Lay them out in a grid. Visually find the frames where the dominant line is closest to your target angle (vertical = 90° from horizontal).

**Step 3** (optional automation): Hough Transform analysis.

```python
import cv2, numpy as np
def dominant_angle(img_path):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3,3), 0), 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=120,
                            minLineLength=80, maxLineGap=20)
    if lines is None: return None
    angles, lengths = [], []
    for l in lines:
        x1,y1,x2,y2 = l[0]
        a = np.degrees(np.arctan2(y2-y1, x2-x1))
        if a < 0: a += 180
        angles.append(a)
        lengths.append(np.hypot(x2-x1, y2-y1))
    bins = np.arange(0, 180, 5)
    hist, _ = np.histogram(angles, bins=bins, weights=lengths)
    return bins[np.argmax(hist)] + 2.5
```

**Caveat**: Hough often picks up background structures (building edges, road segments) rather than the visual "subject" lines. Treat it as a hint — always validate visually.

### Setting the cut frame

Once you know:
- `src_exit` — the perpendicular frame time in clip A
- `src_entry` — the perpendicular frame time in clip B

Compute `src_start` for clip A:
```
src_start_A = src_exit - (out_dur_A × speed_A)
```

Set `src_start` for clip B directly: `src_start_B = src_entry`.

### Tradeoffs

If `src_exit` of clip A doesn't leave enough source for the desired `out_dur`, you need to either:
- Reduce `out_dur`
- Increase `speed` (less slowmo)
- Compromise on the perpendicular frame (pick the next-best)

---

## 2. Rotation matching

Use case: two top-down drone shots, both rotating (yaw) over the ground. If their angular velocities differ, the cut feels jarring even if the orientations align at the cut frame.

### Measurement — ECC or feature matching

For each clip, measure degrees per second of yaw rotation:

```python
import cv2, numpy as np, subprocess
def rotation_between(im_a, im_b):
    orb = cv2.ORB_create(nfeatures=2000)
    kp1, des1 = orb.detectAndCompute(im_a, None)
    kp2, des2 = orb.detectAndCompute(im_b, None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(bf.match(des1, des2), key=lambda m: m.distance)[:200]
    pts1 = np.float32([kp1[m.queryIdx].pt for m in matches])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in matches])
    M, _ = cv2.estimateAffinePartial2D(pts1, pts2, method=cv2.RANSAC)
    if M is None: return None
    return np.degrees(np.arctan2(M[1,0], M[0,0]))

def yaw_rate(clip, t0, t1, step=0.5):
    rates = []
    prev = extract_grayscale(clip, t0)
    t = t0
    while t + step <= t1:
        cur = extract_grayscale(clip, t + step)
        a = rotation_between(prev, cur)
        if a is not None:
            rates.append(a / step)
        prev = cur
        t += step
    return np.mean(rates) if rates else None
```

### Matching speeds

To make effective rotation match across both clips:

```
effective_rotation_A = source_yaw_A × playback_speed_A
effective_rotation_B = source_yaw_B × playback_speed_B

For match: effective_A == effective_B
```

Pick a target effective rotation (e.g. average of both naturals), then:

```python
target = (yaw_A + yaw_B) / 2
playback_A = target / yaw_A
playback_B = target / yaw_B
```

Example from the Interlaken project:
- Clip A (train station rails): 14.14 °/s natural
- Clip B (river bridge): 24.00 °/s natural
- Target: 17.7 °/s (average + a bit faster for energy)
- → A at 1.25× = 17.7 °/s effective ✓
- → B at 0.74× = 17.8 °/s effective ✓

The viewer sees one continuous "rotation" across the cut.

### Combining perpendicular + rotation matching

1. Measure natural yaw rates of both clips
2. Pick target effective rotation
3. Compute playback speeds
4. Find perpendicular frames in each clip
5. Set `src_start_A` = `src_exit_perp_A − out_dur_A × speed_A`
6. Set `src_start_B` = `src_entry_perp_B`

If math doesn't work (e.g. `src_start_A` becomes negative), iterate: pick a different perpendicular frame, or accept rotation mismatch.

## Anti-patterns

- **Forcing a match cut on shots that don't share a structure** → looks contrived
- **Cross-fading instead of cutting** → the form match relies on a HARD CUT. Dissolves destroy it.
- **Heavy speed ramps near the cut** → the velocity discontinuity is what kills the match. Keep speed constant for at least the last 0.5s of clip A and first 0.5s of clip B.

## See also

- [scripts/analyze_rotation.py](../scripts/analyze_rotation.py) — Rotation rate measurement
- [scripts/find_perpendicular.py](../scripts/find_perpendicular.py) — Hough-based perpendicular detection
