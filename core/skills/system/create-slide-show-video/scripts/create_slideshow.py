#!/usr/bin/env python3
"""Create a slideshow video from images with xfade transitions."""

from __future__ import annotations

import argparse
import pathlib
import platform
import re
import shutil
import subprocess
import sys
from typing import Iterable


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")
SUPPORTED_TRANSITIONS = (
    "fade",
    "fadefast",
    "fadeslow",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
    "slideleft",
    "slideright",
    "slideup",
    "slidedown",
    "circlecrop",
    "rectcrop",
    "distance",
    "fadeblack",
    "fadewhite",
    "radial",
    "smoothleft",
    "smoothright",
    "smoothup",
    "smoothdown",
    "circleopen",
    "circleclose",
    "vertopen",
    "vertclose",
    "horzopen",
    "horzclose",
    "dissolve",
    "pixelize",
    "diagtl",
    "diagtr",
    "diagbl",
    "diagbr",
    "hlslice",
    "hrslice",
    "vuslice",
    "vdslice",
    "hlwind",
    "hrwind",
    "vuwind",
    "vdwind",
    "hblur",
    "fadegrays",
    "wipetl",
    "wipetr",
    "wipebl",
    "wipebr",
    "squeezeh",
    "squeezev",
    "zoomin",
    "coverleft",
    "coverright",
    "coverup",
    "coverdown",
    "revealleft",
    "revealright",
    "revealup",
    "revealdown",
    "custom",
)


def natural_key(value: str) -> list[object]:
    parts = re.split(r"(\d+)", value)
    key: list[object] = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part.lower())
    return key


def parse_size(raw: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{2,5})x(\d{2,5})", raw)
    if not match:
        raise ValueError(f"Invalid --size '{raw}'. Expected format WIDTHxHEIGHT, e.g. 1920x1080.")
    return int(match.group(1)), int(match.group(2))


def probe_duration(media_file: pathlib.Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nk=1:nw=1",
            str(media_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def find_matching_audio(image_path: pathlib.Path, audio_dir: pathlib.Path) -> pathlib.Path | None:
    for ext in SUPPORTED_AUDIO_EXTENSIONS:
        candidate = audio_dir / f"{image_path.stem}{ext}"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def ensure_ffmpeg(auto_install: bool) -> None:
    if shutil.which("ffmpeg"):
        return
    if auto_install and platform.system() == "Darwin" and shutil.which("brew"):
        print("ffmpeg not found. Installing with: brew install ffmpeg")
        subprocess.run(["brew", "install", "ffmpeg"], check=True)
        if shutil.which("ffmpeg"):
            return
    raise RuntimeError("ffmpeg is not available. Install it (macOS: brew install ffmpeg) and retry.")


def list_images(directory: pathlib.Path) -> list[pathlib.Path]:
    images = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    images.sort(key=lambda path: natural_key(path.name))
    return images


def build_filter_complex(
    image_count: int,
    width: int,
    height: int,
    image_duration: float,
    transition: str,
    transition_duration: float,
    fps: int,
    has_audio: bool,
    audio_input_index: int,
    audio_fit: str,
    total_duration: float,
    audio_fadeout_duration: float,
) -> str:
    parts: list[str] = []
    for idx in range(image_count):
        parts.append(
            f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"format=yuv420p,setsar=1[v{idx}]"
        )

    if image_count == 1:
        video_stream = "v0"
    else:
        offset = image_duration - transition_duration
        for idx in range(1, image_count):
            left = "v0" if idx == 1 else f"x{idx - 1}"
            right = f"v{idx}"
            out = f"x{idx}"
            parts.append(
                f"[{left}][{right}]xfade=transition={transition}:duration={transition_duration}:"
                f"offset={offset}[{out}]"
            )
            offset += image_duration - transition_duration
        video_stream = f"x{image_count - 1}"

    parts.append(f"[{video_stream}]fps={fps}[vout]")

    if has_audio:
        fadeout_filter = ""
        if audio_fadeout_duration > 0:
            fadeout_start = max(0.0, total_duration - audio_fadeout_duration)
            fadeout_filter = f",afade=t=out:st={fadeout_start}:d={audio_fadeout_duration}"
        if audio_fit == "loop":
            parts.append(f"[{audio_input_index}:a]atrim=duration={total_duration},asetpts=N/SR/TB{fadeout_filter}[aout]")
        else:
            parts.append(f"[{audio_input_index}:a]apad,atrim=duration={total_duration},asetpts=N/SR/TB{fadeout_filter}[aout]")

    return ";".join(parts)


def build_command(
    images: Iterable[pathlib.Path],
    output: pathlib.Path,
    audio: pathlib.Path | None,
    audio_fit: str,
    image_duration: float,
    transition: str,
    transition_duration: float,
    fps: int,
    size: tuple[int, int],
    crf: int,
    preset: str,
    overwrite: bool,
    audio_fadeout_duration: float,
) -> list[str]:
    width, height = size
    images_list = list(images)
    image_count = len(images_list)
    total_duration = image_count * image_duration - (image_count - 1) * transition_duration

    cmd: list[str] = ["ffmpeg", "-hide_banner", "-y" if overwrite else "-n"]

    for image in images_list:
        cmd.extend(["-loop", "1", "-t", str(image_duration), "-i", str(image)])

    audio_input_index = image_count
    if audio:
        if audio_fit == "loop":
            cmd.extend(["-stream_loop", "-1"])
        cmd.extend(["-i", str(audio)])

    filter_complex = build_filter_complex(
        image_count=image_count,
        width=width,
        height=height,
        image_duration=image_duration,
        transition=transition,
        transition_duration=transition_duration,
        fps=fps,
        has_audio=audio is not None,
        audio_input_index=audio_input_index,
        audio_fit=audio_fit,
        total_duration=total_duration,
        audio_fadeout_duration=audio_fadeout_duration,
    )
    cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]"])

    if audio:
        cmd.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])

    cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", preset, "-crf", str(crf), str(output)])
    return cmd


def build_per_image_audio_command(
    pairs: list[tuple[pathlib.Path, pathlib.Path, float]],
    output: pathlib.Path,
    fps: int,
    size: tuple[int, int],
    crf: int,
    preset: str,
    overwrite: bool,
    audio_fadeout_duration: float,
) -> tuple[list[str], float]:
    width, height = size
    n = len(pairs)
    total_duration = sum(duration for _, _, duration in pairs)

    cmd: list[str] = ["ffmpeg", "-hide_banner", "-y" if overwrite else "-n"]
    for image, _, duration in pairs:
        cmd.extend(["-loop", "1", "-t", str(duration), "-i", str(image)])
    for _, audio, _ in pairs:
        cmd.extend(["-i", str(audio)])

    parts: list[str] = []
    for idx in range(n):
        parts.append(
            f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"format=yuv420p,setsar=1,fps={fps}[v{idx}]"
        )

    concat_inputs = "".join(f"[v{idx}][{n + idx}:a]" for idx in range(n))
    parts.append(f"{concat_inputs}concat=n={n}:v=1:a=1[vcat][acat]")

    if audio_fadeout_duration > 0 and total_duration > 0:
        fadeout_start = max(0.0, total_duration - audio_fadeout_duration)
        parts.append(
            f"[acat]afade=t=out:st={fadeout_start}:d={audio_fadeout_duration}[aout]"
        )
        audio_out_label = "aout"
    else:
        audio_out_label = "acat"

    parts.append("[vcat]null[vout]")

    cmd.extend([
        "-filter_complex", ";".join(parts),
        "-map", "[vout]",
        "-map", f"[{audio_out_label}]",
        "-c:a", "aac", "-b:a", "192k",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", preset, "-crf", str(crf),
        str(output),
    ])
    return cmd, total_duration


def build_webp_command(
    input_video: pathlib.Path,
    output_webp: pathlib.Path,
    fps: int,
    size: tuple[int, int],
    quality: int,
    overwrite: bool,
) -> list[str]:
    width, height = size
    return [
        "ffmpeg", "-hide_banner", "-y" if overwrite else "-n",
        "-i", str(input_video),
        "-vf", f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
        "-c:v", "libwebp_anim",
        "-quality", str(quality),
        "-loop", "0",
        "-an",
        str(output_webp),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a slideshow video from ordered images with xfade.")
    parser.add_argument("--images-dir", required=True, type=pathlib.Path, help="Directory of input images.")
    parser.add_argument("--output", required=True, type=pathlib.Path, help="Output video path.")
    parser.add_argument(
        "--audio-mode",
        choices=("none", "background", "per-image"),
        default=None,
        help=(
            "Audio mode. 'none': silent video. 'background': single audio file via --audio. "
            "'per-image': pair each image with an audio file of the same stem in the images dir "
            "(or --per-image-audio-dir); each image's display duration equals its audio's duration. "
            "If omitted, inferred from --audio (background if set, else none)."
        ),
    )
    parser.add_argument("--audio", type=pathlib.Path, default=None, help="Optional background audio file.")
    parser.add_argument(
        "--per-image-audio-dir",
        type=pathlib.Path,
        default=None,
        help="Directory holding per-image audio files (defaults to --images-dir).",
    )
    parser.add_argument(
        "--audio-fit",
        choices=("trim", "loop"),
        default="trim",
        help="How to fit background audio to slideshow duration (background mode only).",
    )
    parser.add_argument("--image-duration", type=float, default=3.0, help="Seconds per image.")
    parser.add_argument(
        "--transition",
        choices=SUPPORTED_TRANSITIONS,
        default="fade",
        help="FFmpeg xfade transition name.",
    )
    parser.add_argument("--transition-duration", type=float, default=0.5, help="Transition duration in seconds.")
    parser.add_argument("--fps", type=int, default=30, help="Output FPS.")
    parser.add_argument("--size", default="1920x1080", help="Output size WIDTHxHEIGHT.")
    parser.add_argument("--crf", type=int, default=20, help="libx264 CRF value.")
    parser.add_argument("--preset", default="medium", help="libx264 preset.")
    parser.add_argument("--audio-fadeout-duration", type=float, default=2.0, help="Audio fade-out duration in seconds at the end (0 to disable).")
    parser.add_argument(
        "--format",
        choices=("mp4", "webp", "both"),
        default="both",
        help="Output format: mp4, webp, or both (default: both).",
    )
    parser.add_argument("--webp-fps", type=int, default=10, help="Frame rate for WebP output.")
    parser.add_argument("--webp-size", default="1280x720", help="Output size for WebP WIDTHxHEIGHT.")
    parser.add_argument("--webp-quality", type=int, default=80, help="Quality for WebP output (0-100).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output file if it exists.")
    parser.add_argument(
        "--no-auto-install-ffmpeg",
        action="store_true",
        help="Do not auto-run 'brew install ffmpeg' when ffmpeg is missing on macOS.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.fps <= 0:
        raise ValueError("--fps must be > 0.")

    if args.audio_mode is None:
        audio_mode = "background" if args.audio is not None else "none"
    else:
        audio_mode = args.audio_mode

    if audio_mode != "per-image":
        if args.image_duration <= 0:
            raise ValueError("--image-duration must be > 0.")
        if args.transition_duration <= 0:
            raise ValueError("--transition-duration must be > 0.")
        if args.transition_duration >= args.image_duration:
            raise ValueError("--transition-duration must be smaller than --image-duration.")

    ensure_ffmpeg(auto_install=not args.no_auto_install_ffmpeg)

    images_dir = args.images_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if not images_dir.exists() or not images_dir.is_dir():
        raise FileNotFoundError(f"Image directory not found: {images_dir}")

    images = list_images(images_dir)
    if len(images) < 1:
        raise ValueError("Need at least 1 image to create slideshow.")
    if audio_mode != "per-image" and len(images) < 2:
        raise ValueError("Need at least 2 images to create xfade slideshow.")

    size = parse_size(args.size)

    if audio_mode == "per-image":
        audio_dir = (args.per_image_audio_dir or args.images_dir).expanduser().resolve()
        if not audio_dir.exists() or not audio_dir.is_dir():
            raise FileNotFoundError(f"Per-image audio directory not found: {audio_dir}")
        pairs: list[tuple[pathlib.Path, pathlib.Path, float]] = []
        missing: list[str] = []
        for image in images:
            match = find_matching_audio(image, audio_dir)
            if match is None:
                missing.append(image.name)
                continue
            duration = probe_duration(match)
            if duration <= 0:
                raise ValueError(f"Audio duration must be > 0 for {match}")
            pairs.append((image, match, duration))
        if missing:
            raise FileNotFoundError(
                "Missing matching audio for images: " + ", ".join(missing) +
                f" (looked in {audio_dir} for extensions {SUPPORTED_AUDIO_EXTENSIONS})"
            )
        cmd, total_duration = build_per_image_audio_command(
            pairs=pairs,
            output=output,
            fps=args.fps,
            size=size,
            crf=args.crf,
            preset=args.preset,
            overwrite=args.overwrite,
            audio_fadeout_duration=args.audio_fadeout_duration,
        )
        print(f"Found {len(pairs)} image+audio pairs in natural order.")
        for image, audio_file, duration in pairs:
            print(f"  {image.name} <- {audio_file.name} ({duration:.3f}s)")
        print(f"Slideshow duration target: {total_duration:.3f}s")
    else:
        audio: pathlib.Path | None = None
        if audio_mode == "background":
            if args.audio is None:
                raise ValueError("--audio is required when --audio-mode=background.")
            audio = args.audio.expanduser().resolve()
            if not audio.exists() or not audio.is_file():
                raise FileNotFoundError(f"Audio file not found: {audio}")

        cmd = build_command(
            images=images,
            output=output,
            audio=audio,
            audio_fit=args.audio_fit,
            image_duration=args.image_duration,
            transition=args.transition,
            transition_duration=args.transition_duration,
            fps=args.fps,
            size=size,
            crf=args.crf,
            preset=args.preset,
            overwrite=args.overwrite,
            audio_fadeout_duration=args.audio_fadeout_duration,
        )
        total_duration = len(images) * args.image_duration - (len(images) - 1) * args.transition_duration
        print(f"Found {len(images)} images in natural order.")
        print(f"Slideshow duration target: {total_duration:.3f}s")

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Created slideshow: {output}")

    if args.format in ("webp", "both"):
        webp_output = output.with_suffix(".webp")
        webp_size = parse_size(args.webp_size)
        webp_cmd = build_webp_command(
            input_video=output,
            output_webp=webp_output,
            fps=args.webp_fps,
            size=webp_size,
            quality=args.webp_quality,
            overwrite=args.overwrite,
        )
        print(f"Converting to WebP ({args.webp_size} @ {args.webp_fps}fps)...")
        print("Running:", " ".join(webp_cmd))
        subprocess.run(webp_cmd, check=True)
        print(f"Created WebP: {webp_output}")
        if args.format == "webp":
            output.unlink()
            print(f"Removed intermediate MP4: {output}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
