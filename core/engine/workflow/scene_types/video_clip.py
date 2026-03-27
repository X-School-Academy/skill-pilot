"""Video clip scene type module for video creation."""

import subprocess
import uuid
from typing import Any, Dict

from ..VideoStyle import VideoStyle
from .shared import get_media_duration, get_or_create_voice_audio, resolve_optional_scene_file


async def create_video_clip_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    """Create a scene from an existing video clip and external narration audio."""
    video_path = resolve_optional_scene_file(scene, "video_path")
    voice_over = scene.get("voice_over", "")
    voice_path = scene.get("voice_path", "")

    if not video_path:
        raise ValueError("Video clip scene requires 'video_path'")
    if not voice_over and not voice_path:
        raise ValueError("Video clip scene requires 'voice_over' or 'voice_path'")

    audio_path, _ = await get_or_create_voice_audio(
        voice_over,
        voice_path,
        style.voice_name,
    )
    if not audio_path:
        raise RuntimeError("Failed to prepare audio for video clip scene")

    scene["voice_url"] = audio_path

    video_duration = max(get_media_duration(video_path), 0.0)
    audio_duration = max(get_media_duration(audio_path), 0.0)
    target_duration = video_duration
    video_filter = (
        f"scale={style.width}:{style.height}:force_original_aspect_ratio=increase,"
        f"crop={style.width}:{style.height},fps=30"
    )

    if audio_duration > video_duration and video_duration > 0:
        target_duration = audio_duration + 2.0
        speed_factor = target_duration / video_duration
        video_filter = f"{video_filter},setpts={speed_factor}*PTS"

    audio_filter = f"apad=pad_dur={max(target_duration - audio_duration, 0.0):.3f}"
    output_path = f"/tmp/video_clip_scene_{uuid.uuid4()}.mp4"
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-filter:v",
        video_filter,
        "-filter:a",
        audio_filter,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-pix_fmt",
        "yuv420p",
        "-ar",
        "48000",
        "-t",
        f"{target_duration:.3f}",
        output_path,
    ]

    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed for video clip scene: {result.stderr}")

    return output_path
