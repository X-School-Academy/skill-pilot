"""Shared helpers for scene file resolution and voice-over audio handling."""

from pathlib import Path
from typing import Tuple

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
