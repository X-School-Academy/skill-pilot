# FFmpeg Slideshow Reference

## Behavior Summary

- Image files are loaded from `--images-dir`.
- Files are sorted in natural order:
  - `1.png, 2.png, ..., 10.png`
  - `a01.png, a02.png, ..., a15.png`
- Default image display duration is `2.0` seconds.
- Every adjacent image pair uses `xfade`.
- Output defaults to `mp4` with `libx264` video and optional `aac` audio.

## Script Arguments

Required:

- `--images-dir`: directory containing images
- `--output`: output video file path

Optional:

- `--audio`: optional audio file path
- `--audio-fit`: `trim` (default) or `loop`
- `--image-duration`: default `2.0`
- `--transition`: FFmpeg xfade transition name, default `fade`
- `--transition-duration`: default `0.5`
- `--fps`: default `30`
- `--size`: output size as `WIDTHxHEIGHT`, default `1920x1080`
- `--crf`: x264 CRF, default `20`
- `--preset`: x264 preset, default `medium`
- `--overwrite`: overwrite output when exists
- `--no-auto-install-ffmpeg`: disable macOS auto-install fallback

## Audio Fit Modes

- Check audio duration first (when audio is provided):

```bash
ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 <audio_file>
```

- `trim`:
  - Keeps single audio input.
  - Uses `apad,atrim` to force exact slideshow duration.
- `loop`:
  - Re-opens audio with `-stream_loop -1`.
  - Trims to exact slideshow duration.

## Creation Plan Template

Before generation, prepare:

- `images`: natural-ordered filenames and count.
- `image_duration`: default `2.0` unless user overrides.
- `transition`: one supported `xfade` transition.
- `transition_duration`: must be `< image_duration`.
- `video_duration`: `image_count * image_duration - (image_count - 1) * transition_duration`.
- `audio_duration`: from `ffprobe` (if audio exists).
- `audio_fit`: `trim` or `loop`.
- `output`: path, size, fps, and encoding requirements.

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

## Example

```bash
core/bin/python core/skills/system/create-slide-show-video/scripts/create_slideshow.py \
  --images-dir assets/slides \
  --output .skillpilot/temp/slide-demo.mp4 \
  --audio assets/music.mp3 \
  --audio-fit trim \
  --image-duration 2 \
  --transition fade \
  --transition-duration 0.5 \
  --overwrite
```
