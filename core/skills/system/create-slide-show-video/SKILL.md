---
name: create-slide-show-video
description: Create slideshow videos from ordered images using FFmpeg xfade transitions, with optional audio that can be trimmed or looped to match slideshow length. Use when users ask to generate image-to-video slideshows.
---

# AI Builder - Create Slide Show Video

This skill creates a slideshow video from images in natural filename order with FFmpeg xfade transitions. It supports optional audio and can trim or loop audio to match slideshow duration.

## When to Use This Skill

- User asks to generate a slideshow video from images.
- User requests transition effects between slides.
- User wants optional background audio matched to slideshow duration.
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
- Optional: confirm audio file path.
- Optional: confirm image duration (default `3.0` seconds).
- Optional: confirm transition type and transition duration.
- Optional: confirm audio fade-out duration (default `2.0` seconds; set to `0` to disable).
- Optional: confirm output format: `mp4`, `webp`, or `both` (default `both`).
- Optional: if audio is provided, confirm audio fit mode:
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

- Record this value for planning.

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

With audio:

```bash
core/bin/python core/skills/system/create-slide-show-video/scripts/create_slideshow.py \
  --images-dir <images_dir> \
  --output <output_video.mp4> \
  --audio <audio_file> \
  --audio-fit loop
```

For each request, check the user's exact requirements first. If the sample helper script cannot fit that request, create a temporary helper script under `.skillpilot/temp/` and run it with:

```bash
core/bin/python .skillpilot/temp/<custom_script>.py ...
```

For all options and transition names, refer to `references/ffmpeg-slideshow.md`.

### Step 6: Verify Output

- Confirm image order is natural (e.g., `1,2,...,10` not `1,10,2`).
- Confirm each image displays for `3` seconds by default.
- Confirm transitions are visible and smooth.
- If audio is enabled, confirm audio is aligned to slideshow length according to `audio-fit`.
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
