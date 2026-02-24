import os
import re
from pathlib import Path
from typing import Any, Optional


_DEFAULT_VOICE_GENDER = "female"
_DEFAULT_VOICE_AGE_BUCKET = "30"
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_VOICE_ASSET_DIR = (_PROJECT_ROOT / "assets" / "voices").resolve()
_DEFAULT_REF_VOICE_FALLBACK = os.getenv(
    "GPU_WORKER_DEFAULT_REF_VOICE",
    str(_VOICE_ASSET_DIR / "voice-female-30yo.mp3"),
)


def _normalize_voice_gender(gender: Optional[str]) -> str:
    normalized = str(gender or "").strip().lower()
    if normalized == "male":
        return "male"
    return "female"


def _resolve_age_bucket(age: Any) -> str:
    numeric_age: Optional[int] = None

    if isinstance(age, (int, float)):
        numeric_age = int(age)
    elif isinstance(age, str):
        digit_match = re.search(r"\d+", age)
        if digit_match:
            numeric_age = int(digit_match.group())

    if numeric_age is None:
        return _DEFAULT_VOICE_AGE_BUCKET
    if numeric_age < 10:
        return "5"
    if numeric_age < 20:
        return "15"
    if numeric_age < 40:
        return "30"
    return "40"


def _build_voice_sample_path(gender: str, age_bucket: str, is_music_voice: bool = False) -> Optional[str]:
    prefix = "song" if is_music_voice else "voice"
    filename = f"{prefix}-{gender}-{age_bucket}yo.mp3"
    candidate_path = _VOICE_ASSET_DIR / filename
    if candidate_path.exists():
        return str(candidate_path)

    if is_music_voice:
        fallback_filename = f"voice-{gender}-{age_bucket}yo.mp3"
        fallback_path = _VOICE_ASSET_DIR / fallback_filename
        if fallback_path.exists():
            return str(fallback_path)

    return None


def get_default_ref_voice(
    task_type: str,
    gender: Optional[str],
    age: Any,
    emotion: Optional[str],
    is_music_voice: bool = False,
) -> str:
    _ = task_type, emotion  # Compatibility placeholders for older call sites.
    normalized_gender = _normalize_voice_gender(gender)
    age_bucket = _resolve_age_bucket(age)

    voice_path = _build_voice_sample_path(normalized_gender, age_bucket, is_music_voice)
    if not voice_path and normalized_gender != _DEFAULT_VOICE_GENDER:
        voice_path = _build_voice_sample_path(_DEFAULT_VOICE_GENDER, age_bucket, is_music_voice)
    if not voice_path:
        voice_path = _build_voice_sample_path(_DEFAULT_VOICE_GENDER, _DEFAULT_VOICE_AGE_BUCKET, is_music_voice)

    return voice_path or _DEFAULT_REF_VOICE_FALLBACK
