"""Shared helpers for scene file resolution and voice-over audio handling."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from llm import LLM
from tts_service import async_text_to_audio_file


REPO_ROOT = Path(__file__).resolve().parents[4]


def resolve_project_file_path(raw_path: str, field_name: str) -> str:
    """Resolve a file path that may be absolute or relative to the repo root."""
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate

    resolved = candidate.resolve()
    if not resolved.is_file():
        raise ValueError(f"{field_name} does not exist: {raw_path}")

    return str(resolved)


def resolve_optional_scene_file(scene: dict, field_name: str) -> str:
    """Resolve and normalize an optional scene file field in place."""
    raw_path = scene.get(field_name, "")
    if not raw_path:
        return ""

    resolved = resolve_project_file_path(raw_path, field_name)
    scene[field_name] = resolved
    return resolved


def copy_file_to_path(source_path: str, destination_path: str) -> str:
    """Copy a local file to a destination path and return the resolved destination."""
    source = Path(source_path).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"Source file does not exist: {source_path}")

    destination = Path(destination_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    if source != destination.resolve(strict=False):
        shutil.copy2(source, destination)

    return str(destination.resolve())


def extract_mcp_text_content(payload: Any) -> Optional[str]:
    """Extract the first text item from an MCP tool response payload."""
    if not isinstance(payload, dict):
        return None

    content = payload.get("content")
    if not isinstance(content, list):
        return None

    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def run_media_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Invoke a local media MCP tool through core/bin/tool-cli and return its output path."""
    request = {
        "server_id": "media",
        "tool_name": tool_name,
        "arguments": arguments,
    }
    result = subprocess.run(
        [str(REPO_ROOT / "core/bin/tool-cli"), "request", json.dumps(request)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Media tool {tool_name} failed: {stderr}")

    output = (result.stdout or "").strip()
    if not output:
        raise RuntimeError(f"Media tool {tool_name} returned no output")

    try:
        response = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Media tool {tool_name} returned invalid JSON: {output}") from exc

    if not isinstance(response, dict):
        raise RuntimeError(f"Media tool {tool_name} returned unexpected response")
    if response.get("status") != "ok":
        raise RuntimeError(str(response.get("detail") or f"Media tool {tool_name} failed"))

    result_payload = response.get("result")
    raw_path = extract_mcp_text_content(result_payload)
    if not raw_path and isinstance(result_payload, str):
        raw_path = result_payload.strip()
    if not raw_path:
        raise RuntimeError(f"Media tool {tool_name} returned no path")

    return raw_path


def probe_media(path: str) -> Dict[str, Any]:
    """Probe media metadata with ffprobe."""
    resolved = resolve_project_file_path(path, "media_path")
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        resolved,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {resolved}: {result.stderr}")
    return json.loads(result.stdout or "{}")


def get_media_duration(path: str) -> float:
    """Get media duration in seconds."""
    payload = probe_media(path)
    duration = (payload.get("format") or {}).get("duration")
    try:
        return float(duration)
    except (TypeError, ValueError):
        return 0.0


def media_has_audio_stream(path: str) -> bool:
    """Return True when ffprobe detects an audio stream."""
    payload = probe_media(path)
    streams = payload.get("streams") or []
    return any(isinstance(stream, dict) and stream.get("codec_type") == "audio" for stream in streams)


async def get_or_create_voice_audio(
    voice_over: str,
    voice_path: str,
    voice_name: str,
) -> Tuple[str, bool]:
    """
    Return an audio file path for a scene voice-over.

    If ``voice_path`` is provided, it is resolved and returned without generating TTS.
    Returns ``(audio_path, should_cleanup_audio)``.
    """
    if voice_path:
        return resolve_project_file_path(voice_path, "voice_path"), False

    try:
        audio_path = await async_text_to_audio_file(
            voice_over,
            voice=voice_name,
            format="wav",
        )
    except Exception as e:
        print(f"Gemini TTS failed, falling back to LLM: {e}")
        async with LLM() as llm:
            audio_path = await llm.text_to_audio_file(
                voice_over,
                voice=voice_name,
            )

    return audio_path, True
