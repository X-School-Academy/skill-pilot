---
name: create-slide-show-video
description: Create slideshow videos from ordered images using FFmpeg. Supports three modes: silent slideshow with xfade transitions, slideshow with a single background audio (trimmed or looped), and slideshow where each image is paired with its own audio file and its on-screen duration equals that audio's duration. Use when users ask to generate image-to-video slideshows.
---

# AI Builder - Create Slide Show Video

This skill creates a slideshow video from images in natural filename order. It supports three audio modes:

1. **Silent** (`--audio-mode none`): images only, with xfade transitions.
2. **Background audio** (`--audio-mode background --audio <file>`): single shared audio, trimmed or looped to slideshow length; xfade transitions between images.
3. **Per-image audio** (`--audio-mode per-image`): each image is paired with an audio file having the same stem (e.g., `a.png` + `a.mp3`/`a.wav`); the image's on-screen duration equals the matching audio's duration. Audios are concatenated in natural image order. No xfade transitions in this mode.

## When to Use This Skill

- User asks to generate a slideshow video from images.
- User requests transition effects between slides.
- User wants optional background audio matched to slideshow duration.
- User wants each image to be narrated/scored by its own audio file (per-image audio mode).
- User needs predictable image ordering like `1.png` to `11.png` or `a01.png` to `a15.png`.

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Build and run the slideshow generation command and helper script.
- **QA Engineer**: Validate ordering, timing, transition behavior, and media output.
- **Technical Writer**: Confirm command arguments and output behavior are documented clearly.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Collect Inputs

- Confirm the input image directory.
- Confirm output video path.
- Confirm audio mode:
  - `none`: silent slideshow.
  - `background`: a single audio file shared across the slideshow (requires `--audio`).
  - `per-image`: each image has a matching audio file with the same stem (`a.png` ↔ `a.mp3`/`a.wav`). Supported audio extensions: `.mp3 .wav .m4a .aac .ogg .flac`. Audio dir defaults to `--images-dir`; override with `--per-image-audio-dir`.
- For `none` / `background`: confirm image duration (default `3.0` seconds), transition type, and transition duration.
- For `per-image`: each image's duration is auto-derived from its audio's duration (use `ffprobe`); transitions are disabled.
- Optional: confirm audio fade-out duration (default `2.0` seconds; set to `0` to disable). Applies at the end of the final audio in all modes.
- Optional: confirm output format: `mp4`, `webp`, or `both` (default `both`).
- For `background`: confirm audio fit mode:
  - `trim`: trim/pad audio to slideshow length
  - `loop`: loop audio then trim to slideshow length

### Step 2: Ensure FFmpeg Exists

- Check FFmpeg:
  - `ffmpeg -version`
- Check FFprobe:
  - `ffprobe -version`
- If FFmpeg is missing on macOS, install it with:
  - `brew install ffmpeg`

### Step 3: Check Audio Duration (If Audio Exists)

- If audio is provided, get precise duration with:

```bash
ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 <audio_file>
```

- For `background` mode: record this value for planning.
- For `per-image` mode: probe every matching audio file; the script does this automatically and uses each duration as the corresponding image's on-screen time.

### Step 4: Make a Creation Plan

Before generating, write a short plan that includes:

- Ordered image list and image count.
- Slide duration (default `3.0s` unless user requests otherwise).
- Transition type and transition duration.
- Computed slideshow target duration.
- Audio duration from `ffprobe` (if audio exists).
- Audio handling decision:
  - `trim`: trim or pad audio to slideshow duration.
  - `loop`: loop then trim audio to slideshow duration.
- Output codec/container settings if user has specific requirements.

### Step 5: Generate the Slideshow

Treat the bundled helper script as a sample baseline:

```bash
core/bin/python core/skills/system/create-slide-show-video/scripts/create_slideshow.py \
  --images-dir <images_dir> \
  --output <output_video.mp4>
```

With background audio:

```bash
core/bin/python core/skills/system/create-slide-show-video/scripts/create_slideshow.py \
  --images-dir <images_dir> \
  --output <output_video.mp4> \
  --audio-mode background \
  --audio <audio_file> \
  --audio-fit loop
```

With per-image audio (each image displays for the length of its matching audio):

```bash
core/bin/python core/skills/system/create-slide-show-video/scripts/create_slideshow.py \
  --images-dir <images_dir> \
  --output <output_video.mp4> \
  --audio-mode per-image
```

Optional `--per-image-audio-dir <dir>` if audio files live in a different directory than the images.

For each request, check the user's exact requirements first. If the sample helper script cannot fit that request, create a temporary helper script under `.skillpilot/temp/` and run it with:

```bash
core/bin/python .skillpilot/temp/<custom_script>.py ...
```

For all options and transition names, refer to `references/ffmpeg-slideshow.md`.

### Step 6: Verify Output

- Confirm image order is natural (e.g., `1,2,...,10` not `1,10,2`).
- `none` / `background`: confirm each image displays for `3` seconds by default and transitions are visible and smooth.
- `background`: confirm audio is aligned to slideshow length according to `audio-fit`.
- `per-image`: confirm each image's on-screen time equals its matching audio's duration, and the audio plays at the right slide.
- Confirm output file exists and is playable.

## Expected Output

- Output controlled by `--format` (default `both`):
  - `mp4`: H.264/AAC `.mp4` only.
  - `webp`: animated `.webp` only (MP4 generated as intermediate then removed).
  - `both`: both `.mp4` and `.webp` produced side-by-side.
- WebP defaults: 10fps, 1280×720, quality 80 (override with `--webp-fps`, `--webp-size`, `--webp-quality`).
- Logs showing ordered image list, computed duration, and executed FFmpeg commands.

## Key Principles

- Keep slide order deterministic via natural sort.
- Use xfade for visual transitions between every adjacent pair of images.
- Default to `3.0s` per image unless user requests otherwise.
- Apply a 2.0s audio fade-out at the end by default (disable with `--audio-fadeout-duration 0`).
- Default `--format both`: produce both MP4 and animated WebP (10fps, 1280×720, quality 80).
- Keep behavior explicit and reproducible through script arguments.
