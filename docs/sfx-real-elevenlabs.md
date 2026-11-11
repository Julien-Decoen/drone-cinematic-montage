# Real SFX via ElevenLabs Sound Generation API

The original skill used synthetic SFX (lavfi noise + tone). For a more professional / cinematic result, generate real SFX via the **ElevenLabs Sound Generation API**.

Costs roughly $0.0005/sec of generated audio (~$0.10 for a full montage's SFX library).

## Setup

1. Register at https://elevenlabs.io · grab API key from Settings → API
2. Store key securely (never commit / never log):
   ```bash
   echo "sk_..." > /tmp/.el_key
   chmod 600 /tmp/.el_key
   ```

3. API call template:
   ```bash
   curl -sL -X POST \
     -H "xi-api-key: $(cat /tmp/.el_key)" \
     -H "Content-Type: application/json" \
     -d '{"text":"...","duration_seconds":N}' \
     -o output.mp3 \
     https://api.elevenlabs.io/v1/sound-generation
   ```

- Max duration per call: **22 seconds** · charges 20 credits/sec
- Free tier: 10 000 credits (~500s, enough for one project)
- HTTP 401 with `quota_exceeded` → out of credits

## Prompt engineering — the cinematic ambient style

ElevenLabs sound generation responds strongly to:
- **scene specificity** ("alpine swiss forest" not "forest")
- **count constraints** ("1 or 2 birds" not "birds")
- **distance/POV** ("recorded from far distance" / "drone view from high altitude")
- **negative constraints** ("no horn", "no music", "no people")
- **style modifiers** ("peaceful", "cinematic ambient", "minimal", "subtle")

### Rules learned in production

| ❌ Too generic | ✅ Scene-specific |
|---|---|
| "train sound" | "vintage swiss alpine cog railway at 5 km/h, very slow wheel clack" |
| "wind" | "subtle alpine wind whisper, almost imperceptible mountain breeze" |
| "birds" | "two or three small alpine birds chirping gently in distant swiss forest" |
| "cars" | "drone view from very high altitude, one or two cars driving on alpine road far below" |
| "waterfall" | "small alpine swiss waterfall with gentle modest water flow, not too powerful" |

### Always include

- Style anchor: `cinematic ambient`
- Volume hint: `at moderate volume not silent` (ElevenLabs tends to generate too quiet otherwise)
- Negative: `no music`, `no horn`, `no people` as appropriate

### Distance-based SFX variants

For the same subject at different camera distances:

```
cars_far    : "drone view from very high altitude, one or two cars driving on alpine road far below"
cars_mid    : "cars driving by on swiss mountain road, medium distance"
cars_close  : "cars driving on road at close distance, defined engines"
```

Drone perspective (following / passing / above):

```
cars_passing_high      : POV high above, cars passing through frame
cars_following_drone   : POV following one car driving away, smooth engine
```

## Reference prompts (Interlaken project)

See `templates/elevenlabs_prompts.json` for the full set of prompts that gave good results. Reuse as starting point for similar projects.

## Loading real SFX in the script

Replace `make_sfx` lavfi calls with file-based input + cache:

```python
def make_sfx(sfx_type, dur, out_path):
    """V20+ : load from real SFX library + apply gain calibration."""
    # cache hit
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        return
    src = f"{SFX_DIR}/{sfx_type}.mp3"
    gain = CALIBRATION_GAINS.get(sfx_type, 0.0)
    fade_in = 0.4
    fade_out = max(0.4, dur * 0.12)
    return run([FFMPEG, "-y",
                "-stream_loop", "-1", "-i", src,
                "-af", (f"atrim=duration={dur},"
                        f"afade=t=in:st=0:d={fade_in},"
                        f"afade=t=out:st={dur-fade_out}:d={fade_out},"
                        f"volume={gain}dB"),
                "-t", str(dur), "-ar", "44100", "-ac", "2",
                out_path])
```

`-stream_loop -1` lets short source files loop to cover any output duration. `atrim` then exact-trims to the plan length.

## Pitfalls

1. **Volume varies wildly** — Some ElevenLabs SFX come out at -50 dB mean, others -10 dB. **Always measure and calibrate** (see [audio-mixing.md](audio-mixing.md)).
2. **Subtle prompts produce noise floor** — "extremely subtle wind" → near-silence with high noise. Use "subtle but clearly audible".
3. **High gain (>+20 dB)** amplifies the noise floor of quiet recordings. Cap calibration gains at +18-22 dB.
4. **The same prompt twice produces different files** — generate once, cache.
5. **Quota — track usage** : 6 SFX × 10s = 1200 credits = ~12% of free tier. Plan ~15 SFX max per project.

## When real ≠ best

Real SFX from ElevenLabs sometimes feels too "natural" against a synthesized cinematic ambient track. The synthetic recipes in the original `make_sfx` (sine drones, filtered noise) can blend better in some contexts (especially the "drone propeller idle" hum for the outro). Keep both options available.
