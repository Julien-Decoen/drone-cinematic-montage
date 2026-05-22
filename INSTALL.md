# Installation

## Option A — Install as a Claude Code skill (recommended)

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/<your-user>/drone-cinematic-montage.git
```

Restart Claude Code. In any session, ask:

> "Build a cinematic montage from drone clips in `~/Documents/drone/MyTrip/` with `~/Documents/drone/MyTrip/music.mp3`"

Claude should auto-load the skill (matching trigger phrases in [SKILL.md](SKILL.md)).

## Option B — Use the script standalone

```bash
git clone https://github.com/<your-user>/drone-cinematic-montage.git
cd drone-cinematic-montage

# Copy + customize
cp examples/interlaken_v16.py my_project.py
# Edit CLIPS path, MUSIC path, EDIT list, CLIP_GRADE

# Render preview
QUALITY=preview python3 my_project.py

# When happy:
QUALITY=final python3 my_project.py
```

## Dependencies

Install with Homebrew (macOS) or apt (Linux):

```bash
# Required
brew install ffmpeg python@3.12

# Python deps (use pip or pip3)
pip install pillow                    # title/credits PNG generation
pip install opencv-python numpy       # only for analysis scripts (rotation/perpendicular)
```

### macOS notes

If using `/opt/homebrew/bin/ffmpeg` (default Apple Silicon path), the script paths assume this location. On Intel macOS or Linux, update `FFMPEG` and `FFPROBE` constants in the script.

### LUT file (optional)

The reference script uses a `.cube` LUT from "The Ultimate Bundle - HV Presets / Orange Teal / Orange & Teal (9).cube". You can:
- Bring your own `.cube` file
- Use any free LUT (e.g. from https://luts.iwltbap.com/)
- Disable LUT by setting `LUT_SRC = None` and using `lut_strength=0` in CLIP_GRADE

### Fonts (for title overlays)

Default fonts: HelveticaNeue + Didot (macOS bundled). On Linux, replace with:

```python
FONT       = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_DIDOT = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
```

## Verify install

```bash
ffmpeg -version | head -1                # should be 6.0+
python3 -c "from PIL import Image; print('PIL OK')"
python3 -c "import cv2; print(cv2.__version__)"   # for analysis scripts
```

## First run

Try the reference example (won't render without your clips, but checks the script parses):

```bash
python3 -c "
import ast
with open('examples/interlaken_v16.py') as f:
    ast.parse(f.read())
print('✓ script parses cleanly')
"
```
