"""Host speech clip scene type module for video creation."""

from pathlib import Path
from typing import Any, Dict

from ..VideoStyle import VideoStyle
from .shared import (
    get_or_create_voice_audio,
    media_has_audio_stream,
    resolve_optional_scene_file,
    run_media_tool,
)


async def create_host_speech_clip_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    """Create a host speech clip scene using local media MCP tools when needed."""
    video_type = str(scene.get("video_type") or "talk_video").strip() or "talk_video"
    video_path = resolve_optional_scene_file(scene, "video_path")
    host_image_path = resolve_optional_scene_file(scene, "host_image_path")
    voice_over = scene.get("voice_over", "")
    voice_path = scene.get("voice_path", "")
    talking_video_prompt = str(scene.get("talking_video_prompt") or "").strip() or "natural talking video"

    if video_type not in {"talk_video", "lipsync"}:
        raise ValueError("Host speech clip scene supports video_type 'talk_video' or 'lipsync'")

    if video_path and media_has_audio_stream(video_path):
        return video_path

    if not voice_over and not voice_path:
        raise ValueError("Host speech clip scene requires 'voice_over' or 'voice_path'")

    audio_path, _ = await get_or_create_voice_audio(
        voice_over,
        voice_path,
        style.voice_name,
    )
    if not audio_path:
        raise RuntimeError("Failed to prepare audio for host speech clip scene")

    scene["voice_url"] = audio_path

    if video_path:
        tool_name = "video_to_talk_video" if video_type == "talk_video" else "video_lipsync"
        arguments = {
            "video_file": video_path,
            "audio_file": audio_path,
        }
        if tool_name == "video_to_talk_video":
            arguments.update(
                {
                    "prompt": talking_video_prompt,
                    "width": style.width,
                    "height": style.height,
                    "pingpong": True,
                }
            )
        else:
            arguments.update({"label": str(scene.get("scene_id") or ""), "pingpong": True})

        output_path = run_media_tool(tool_name, arguments)
        scene["generated_video_url"] = output_path
        return output_path

    if not host_image_path:
        raise ValueError("Host speech clip scene requires 'host_image_path' or 'host_image_prompt'")

    # When no source video exists, fall back to image-driven talk video even if lipsync was requested.
    output_path = run_media_tool(
        "image_to_talk_video",
        {
            "prompt": talking_video_prompt,
            "image_file": host_image_path,
            "audio_file": audio_path,
            "width": style.width,
            "height": style.height,
        },
    )
    scene["generated_video_url"] = output_path
    if video_type == "lipsync":
        scene["video_type"] = "talk_video"
    return output_path
