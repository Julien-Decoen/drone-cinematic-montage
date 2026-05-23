# YouTube Delivery — Complete Publishing Kit

The film is rendered. Now: thumbnail, title, description, banner, tags. The package that determines whether anyone watches.

## 1. Thumbnail

### Specifications
- Resolution: **1920×1080** (YouTube recommended), 1280×720 minimum
- Format: JPG (smaller file = faster load) at quality 92
- Max file size: 2 MB

### Design principles for cinematic drone

The thumbnail should:
- **Be readable at 320×180** (mobile preview size)
- **Have ONE hero element** — not 5 things competing
- **Match the film's tone** — cinematic minimalist, not YouTube garish

For a Lou_Juicy-style channel:
- ✅ Didot italic title text (cinema feel)
- ✅ Hero landscape from the film (lake, mountain, castle)
- ✅ Subtle subtitle below in Helvetica Light
- ✅ Bottom 40% darkened gradient for text readability
- ❌ No "shocked face" emoji
- ❌ No bright red arrows
- ❌ No "MUST SEE" all-caps

### Template

```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter

THUMB_W, THUMB_H = 1920, 1080
FONT_DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
FONT       = "/System/Library/Fonts/HelveticaNeue.ttc"

def make_thumbnail(source_video, t_extract, main_text, sub_text, output_path):
    # Extract hero frame
    subprocess.run([FFMPEG, "-y", "-ss", str(t_extract), "-i", source_video,
                    "-vframes", "1", "-vf", f"scale={THUMB_W}:{THUMB_H}", "_raw.png"])
    
    bg = Image.open("_raw.png").convert("RGB")
    
    # Gradient overlay bottom 40% (text readability)
    overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    for y in range(int(THUMB_H * 0.6), THUMB_H):
        alpha = int(180 * (y - THUMB_H * 0.6) / (THUMB_H * 0.4))
        d.line([(0, y), (THUMB_W, y)], fill=(0,0,0,alpha))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    
    d = ImageDraw.Draw(bg)
    f_main = ImageFont.truetype(FONT_DIDOT, 220, index=0)
    f_sub  = ImageFont.truetype(FONT, 60, index=4)
    
    # Center-bottom main + sub
    bb = d.textbbox((0,0), main_text, font=f_main)
    main_x = (THUMB_W - (bb[2]-bb[0])) // 2 - bb[0]
    main_y = int(THUMB_H * 0.62) - bb[1]
    d.text((main_x, main_y), main_text, font=f_main, fill=(250,250,250))
    
    bb = d.textbbox((0,0), sub_text, font=f_sub)
    sub_x = (THUMB_W - (bb[2]-bb[0])) // 2 - bb[0]
    sub_y = main_y + (bb[3]-bb[1]) + 40 + 220  # approx
    d.text((sub_x, sub_y), sub_text, font=f_sub, fill=(220,220,220))
    
    bg.save(output_path, "JPEG", quality=92)
```

### Generating thumbnail candidates

Pick 4 candidate moments from the film and let user choose:

```python
CANDIDATES = [
    ("lake_atmosphere", t=8.0,   "atmospheric morning lake"),
    ("castle_reveal",   t=142.0, "iconic landmark"),
    ("cascade",         t=80.0,  "powerful water"),
    ("lake_reveal",     t=35.0,  "vast horizon"),
]
```

Build a 2×2 grid for comparison and present.

## 2. Title

### Structure

```
[LOCATION] — [Storytelling angle] | [Quality/Gear keyword]
```

Examples:
- `INTERLAKEN — Switzerland From Above | Cinematic Drone Film 4K`
- `LAKE COMO — A Higher Perspective | DJI Mini 4 Pro`
- `LOFOTEN — Where The World Ends | 4K Drone Cinematic`

Rules:
- **Location FIRST** (SEO) and in CAPS for visibility
- **Em dash** (—) separates location from descriptor (more cinematic than colon `:`)
- **Pipe** (|) before technical keyword
- **Max 60 chars** (full visibility on mobile)
- **English** for international reach

### Title don'ts

❌ Click-bait: `INSANE drone shots will blow your MIND`
❌ Year-stamped (ages fast): `Switzerland 2026 drone tour`
❌ Vague: `Beautiful drone footage`

## 3. Description

### Structure

```
[Tagline or opening hook]

[2-3 sentences about the trip / location / mood]

📍 [Specific locations comma-separated]
🎥 [Drone gear]
🤖 [Editing tools — sets you apart]
🎵 Music: [Title — Artist]
   → [Direct link to music]

Chapters
[MM:SS Description per Act]
...

Follow the journey
📷 [Instagram or other]

#Tag1 #Tag2 #Tag3 #Tag4 #Tag5
```

### Reference (Interlaken)

```
The world feels bigger from up here.

Three days flying over Interlaken — between Lake Brienz and Lake Thun,
where the Bernese Alps meet the water. Castles, cascades, mist-covered
shores, alpine villages.

📍 Brienz · Iseltwald · Oberhofen · Interlaken, Switzerland
🎥 DJI Mini 4 Pro
🤖 Edited with Claude AI
🎵 Music: Nastelbom — "Cinematic Ambient"
   → https://pixabay.com/fr/music/.../cinematic-ambient-501722/

Chapters
00:00 Awakening — Lake Brienz at dawn
00:18 Discovery — Alpine villages
00:37 Movement — Train station & bridges
01:14 Cascade — Where the mountain falls
01:50 Lake — Sailing on calm water
02:09 Finale — Castles of Oberhofen

Follow the journey
📷 https://www.instagram.com/lou_juicy/

#DroneFilm #Switzerland #Interlaken #DJI #Cinematic
```

### Why this works

- Hook first line (tagline echoing channel brand)
- Concrete locations make it findable by people who know Interlaken
- Specific gear (DJI Mini 4 Pro) attracts that demographic
- Music credit is the legal requirement — make it clean
- Chapters are KILLER for YouTube algorithm + watch time
- IG link converts subscribers across platforms

## 4. Channel banner

### Specifications
- Size: **2560×1440**
- Format: JPG quality 92
- Max file size: 6 MB
- **Safe area for ALL devices**: 1235×338 centered
- **Tablet safe area**: 1546×423 centered

Anything outside the 1235×338 center area might be cropped on mobile.

### Design for a drone channel

- Wide cinematic landscape (16:9 stretched to 2560×1440)
- **Cinema letterbox bars** top/bottom (240px each) — instant film feel
- **Tagline only** in safe center area (don't include channel name — it's already displayed by YouTube above the banner)
- Didot italic for poetic feel, or Helvetica Light for modern minimalist

### Anti-patterns

- Channel name TWICE (banner + YouTube layout)
- Too much text — banner should be CONTEMPLATIVE, not informative
- Photo of the creator's face — for a "travel artist" channel, the LANDSCAPE is the protagonist
- Multiple call-to-action buttons rendered on the image — they get cropped

### Tagline writing

Aim for 4-7 words, in English, that captures the channel's emotional pitch:

- ❌ Too generic: "Drone videos from around the world"
- ❌ Too long: "Cinematic 4K drone films from beautiful locations in Europe"
- ✅ Just right: "The world feels bigger from up here"
- ✅ Just right: "Where every story begins from above"
- ✅ Just right: "A higher perspective on Earth"

## 5. Channel description (About page)

```
[Tagline as first line — anchor]

[Channel description — 2-3 sentences]

[Specs/gear short]

[Social links]
```

Reference:

```
Cinematic drone films from above.
The world feels bigger from up here.

A travel artist taking aerial perspectives on
the world's most striking landscapes.
Hand-edited montages · Natural sound design · Slow cinematic rhythm.

🎥 DJI Mini 4 Pro
🌍 New film when a place has been remembered

📷 @lou_juicy on Instagram
```

## 6. Tags (YouTube Studio)

10-15 specific tags. Order: location-specific → category → gear → style.

Reference:
```
interlaken drone, switzerland from above, cinematic drone film,
dji mini 4 pro, swiss alps drone, bernese oberland, lake brienz,
lake thun, oberhofen castle, aerial photography switzerland,
4k drone footage, cinematic ambient, drone montage, travel film
```

Avoid:
- Generic tags ("drone", "video", "4k") — too competitive
- Tag stuffing — YouTube weights diminishing returns after 15
- Misleading tags (using "DJI Mavic" when you used a Mini)

## 7. End screens & cards

YouTube End Screen (last 5-20 seconds):
- 1 video element (suggested next watch — your previous drone film)
- 1 subscribe element
- Optionally 1 playlist element

End screen images: use stills from each linked video — keep cinematic theme.

## 8. Publishing checklist

Before clicking publish:

- [ ] Video file: 4K H.264 + AAC, max bitrate ~50 Mbps, +faststart flag
- [ ] Thumbnail: 1920×1080 JPG, quality 92
- [ ] Title: location-first, ≤60 chars
- [ ] Description: hook + locations + gear + music + chapters + socials
- [ ] Tags: 10-15 specific
- [ ] Category: Travel & Events (or People & Blogs if more personal)
- [ ] Visibility: Public · scheduled for an evening (best engagement)
- [ ] Comments: ON
- [ ] Captions: auto-gen then review — or upload manually for accuracy
- [ ] End screen with previous video + subscribe
- [ ] Instagram/social pre-tease 6-24h before publish

## 9. Cross-platform deliverables (recap)

For each project, generate:

| Asset | Format | Where |
|---|---|---|
| **YouTube 4K master** | 3840×2160 H.264 ~40 Mbps | YouTube main upload |
| **Instagram Reels 9:16** | 1080×1920 60s | IG Reels (see [instagram-vertical.md](instagram-vertical.md)) |
| **Instagram feed 1:1** | 1080×1080 60s teaser | IG feed |
| **Thumbnail** | 1920×1080 JPG | YouTube |
| **Banner** | 2560×1440 JPG | YouTube channel |
| **Stills** | various | Press / portfolio / IG carousel |
