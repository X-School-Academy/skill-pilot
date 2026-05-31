# FFmpeg Slideshow Reference

## Behavior Summary

- Image files are loaded from `--images-dir`.
- Files are sorted in natural order:
  - `1.png, 2.png, ..., 10.png`
  - `a01.png, a02.png, ..., a15.png`
- Default image display duration is `3.0` seconds (overridable via `--image-duration`).
- In `none` and `background` audio modes, every adjacent image pair uses `xfade`.
- In `per-image` audio mode, each image is paired with an audio file of the same stem; the image's on-screen duration equals its audio's duration; images are joined with the `concat` filter (no xfade).
- Output defaults to `both` (mp4 + animated webp). Use `--format mp4` or `--format webp` to restrict.

## Script Arguments

Required:

- `--images-dir`: directory containing images
- `--output`: output video file path

Optional:

- `--audio-mode`: `none`, `background`, or `per-image`. If omitted, inferred as `background` when `--audio` is set, else `none`.
- `--audio`: audio file path (used in `background` mode).
- `--per-image-audio-dir`: directory holding per-image audio files (defaults to `--images-dir`). Supported audio extensions: `.mp3 .wav .m4a .aac .ogg .flac`.
- `--audio-fit`: `trim` (default) or `loop` — background mode only.
- `--audio-fadeout-duration`: default `2.0` seconds (set to `0` to disable). Applies to the end of the (concatenated) audio in all audio modes.
- `--image-duration`: default `3.0` — applies to `none` and `background` modes only. In `per-image` mode, each image's duration is derived from its matching audio.
- `--transition`: FFmpeg xfade transition name, default `fade` — `none` and `background` modes only.
- `--transition-duration`: default `0.5` — `none` and `background` modes only.
- `--fps`: default `30`
- `--size`: output size as `WIDTHxHEIGHT`, default `1920x1080`
- `--crf`: x264 CRF, default `20`
- `--preset`: x264 preset, default `medium`
- `--format`: `mp4`, `webp`, or `both` (default `both`).
- `--webp-fps`: default `10`
- `--webp-size`: default `1280x720`
- `--webp-quality`: default `80`
- `--overwrite`: overwrite output when exists
- `--no-auto-install-ffmpeg`: disable macOS auto-install fallback

## Audio Modes

Use `ffprobe` to inspect duration of any audio file:

```bash
ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 <audio_file>
```

### `none`
Silent slideshow with xfade transitions.

### `background`
Single shared audio file across the whole slideshow. Audio is fit to slideshow duration with `--audio-fit`:

- `trim`: keeps single audio input; uses `apad,atrim` to force exact slideshow duration.
- `loop`: re-opens audio with `-stream_loop -1`, then trims to exact slideshow duration.

### `per-image`
Each image is paired with an audio file of the same stem in `--per-image-audio-dir` (default: `--images-dir`).

- Lookup order tries `.mp3 .wav .m4a .aac .ogg .flac`.
- The script probes each audio with `ffprobe` and sets the corresponding image's display duration to that audio's duration.
- Images and audios are joined via the `concat` filter (no xfade transitions).
- Total slideshow duration = sum of all per-image audio durations.
- `--audio-fadeout-duration` applies at the end of the concatenated audio.
- If any image lacks a matching audio file, the script fails with the list of unmatched images.

## Creation Plan Template

Before generation, prepare:

- `images`: natural-ordered filenames and count.
- `audio_mode`: `none`, `background`, or `per-image`.
- For `none` / `background`:
  - `image_duration`: default `3.0` unless user overrides.
  - `transition`: one supported `xfade` transition.
  - `transition_duration`: must be `< image_duration`.
  - `video_duration`: `image_count * image_duration - (image_count - 1) * transition_duration`.
- For `background`:
  - `audio_duration`: from `ffprobe`.
  - `audio_fit`: `trim` or `loop`.
- For `per-image`:
  - List of `(image, matched_audio, audio_duration)` tuples; each `image_duration[i] = audio_duration[i]`.
  - `video_duration`: sum of all `audio_duration[i]`.
- `output`: path, size, fps, format, and encoding requirements.

## Transition Notes

- `transition-duration` must be smaller than `image-duration`.
- Slideshow total duration is:
  - `image_count * image_duration - (image_count - 1) * transition_duration`
- Supported transitions:
  - `fade`
  - `fadefast`
  - `fadeslow`
  - `wipeleft`
  - `wiperight`
  - `wipeup`
  - `wipedown`
  - `slideleft`
  - `slideright`
  - `slideup`
  - `slidedown`
  - `circlecrop`
  - `rectcrop`
  - `distance`
  - `fadeblack`
  - `fadewhite`
  - `radial`
  - `smoothleft`
  - `smoothright`
  - `smoothup`
  - `smoothdown`
  - `circleopen`
  - `circleclose`
  - `vertopen`
  - `vertclose`
  - `horzopen`
  - `horzclose`
  - `dissolve`
  - `pixelize`
  - `diagtl`
  - `diagtr`
  - `diagbl`
  - `diagbr`
  - `hlslice`
  - `hrslice`
  - `vuslice`
  - `vdslice`
  - `hlwind`
  - `hrwind`
  - `vuwind`
  - `vdwind`
  - `hblur`
  - `fadegrays`
  - `wipetl`
  - `wipetr`
  - `wipebl`
  - `wipebr`
  - `squeezeh`
  - `squeezev`
  - `zoomin`
  - `coverleft`
  - `coverright`
  - `coverup`
  - `coverdown`
  - `revealleft`
  - `revealright`
  - `revealup`
  - `revealdown`
  - `custom`

## Requirement Fit Rule

- Always validate the user's exact request before generation.
- Use the bundled script as baseline only.
- If baseline script cannot satisfy the request, create a temp helper in `.skillpilot/temp/` and execute via:
  - `core/bin/python .skillpilot/temp/<custom_script>.py ...`

## Examples

Silent slideshow:

```bash
core/bin/python core/skills/system/create-slide-show-video/scripts/create_slideshow.py \
  --images-dir assets/slides \
  --output .skillpilot/temp/slide-demo.mp4 \
  --audio-mode none \
  --image-duration 3 \
  --transition fade \
  --transition-duration 0.5 \
  --overwrite
```

Background audio (trim to slideshow length):

```bash
core/bin/python core/skills/system/create-slide-show-video/scripts/create_slideshow.py \
  --images-dir assets/slides \
  --output .skillpilot/temp/slide-demo.mp4 \
  --audio-mode background \
  --audio assets/music.mp3 \
  --audio-fit trim \
  --image-duration 2 \
  --transition fade \
  --transition-duration 0.5 \
  --overwrite
```

Per-image audio (`assets/slides/a.png` ↔ `a.mp3`, `b.png` ↔ `b.wav`, ...):

```bash
core/bin/python core/skills/system/create-slide-show-video/scripts/create_slideshow.py \
  --images-dir assets/slides \
  --output .skillpilot/temp/slide-demo.mp4 \
  --audio-mode per-image \
  --overwrite
```
