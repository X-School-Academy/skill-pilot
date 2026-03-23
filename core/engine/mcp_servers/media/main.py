"""
Video MCP Server

Provides 20 video/audio processing tools via MCP protocol using fastmcp.
Input and output artifacts are exchanged with ComfyUI through its upload/view HTTP APIs.
Server transport: stdio
"""

import asyncio
import base64
import binascii
from contextlib import asynccontextmanager
import json
import json5
import math
import mimetypes
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

# Ensure core/engine/ is on sys.path regardless of invocation style:
#   python -m mcp_servers.media.main  (already on path)
#   uv run mcp_servers/media/main.py  (only script dir is on path)
_engine_root = str(Path(__file__).resolve().parents[2])
if _engine_root not in sys.path:
    sys.path.insert(0, _engine_root)

from fastmcp import FastMCP

from logger import get_logger
from mcp_servers.media.audio_utils import get_audio_duration
from mcp_servers.media.gpu_workflow_executor import WorkflowExecutor, WorkflowExecutionError
from mcp_servers.media.playwright_utils.html2image import capture_image
from mcp_servers.media.playwright_utils.screen_recording import record_screen
from mcp_servers.media.script_executor import (
    ScriptExecutor,
    ScriptExecutionError
)


REQUIRED_ENV_VARS = {
    "COMFYUI_SERVER_ADDRESS": "Address of the ComfyUI server",
    "COMFYUI_INSTALL_PATH": "ComfyUI installation root path on the remote GPU worker",
    "GPU_WORKER_TTS_CREATOR": "Path to the speech synthesis helper script on ComfyUI server",
    "GPU_WORKER_SONG_CREATOR": "Path to the singing voice helper script on ComfyUI server",
    "GPU_WORKER_LLM_VISION_INFER": "Path to the local vision/LLM helper script on ComfyUI server",
    "GPU_WORKER_WHISPER_CLI": "Path to the Whisper audio transcription script on ComfyUI server",
    "GPU_WORKER_MUSETALK_CLI": "Path to the MuseTalk lip-sync script on ComfyUI server",
    "GPU_WORKER_DEMUCS_CLI": "Path to the Demucs vocal extraction script on ComfyUI server",
}

def _load_env_from_mcp_config() -> None:
    """If COMFYUI_SERVER_ADDRESS is unset, load media env vars from config/mcp.json5."""
    if os.getenv("COMFYUI_SERVER_ADDRESS"):
        return
    config_path = Path(__file__).parents[4] / "config" / "mcp.json5"
    if not config_path.exists():
        return
    try:
        with config_path.open(encoding="utf-8") as f:
            data = json5.load(f)
        env_vars = data.get("mcpServers", {}).get("media", {}).get("env", {})
        for key, value in env_vars.items():
            if not os.getenv(key):
                os.environ[key] = str(value)
    except Exception:
        pass  # Best-effort; missing vars will be caught by _ensure_required_environment


def _ensure_required_environment() -> None:
    missing = []
    for var, description in REQUIRED_ENV_VARS.items():
        value = os.getenv(var)
        if not value:
            missing.append(f"{var} ({description})")

    if missing:
        details = ", ".join(missing)
        raise RuntimeError(
            "Missing required environment variables for the Video MCP server: "
            f"{details}."
        )


log = get_logger("mcp_video.video")
_comfy_install_path: str = ""
_comfy_remote_input_dir: str = ""
_comfy_remote_output_dir: str = ""


# Initialize MCP server
mcp = FastMCP("Video Processing Server")

# Initialize processors
workflow_executor = WorkflowExecutor()
script_executor = ScriptExecutor()

MAX_LIPSYNC_AUDIO_SECONDS = 3 * 60
DEFAULT_VIDEO_FPS = 25

DEFAULT_MUSETALK_MAX_AUDIO_SECONDS = 60 * 60 * 2

# File serving security cache - only allow fetching files registered here
_allowed_output_files: set[str] = set()
_comfy_server_base_url: str = ""
_uploaded_input_files: dict[str, str] = {}
_downloaded_input_files: dict[str, str] = {}
_uploaded_to_comfy_files: dict[str, str] = {}
_download_dir = Path("/tmp/mcp_video_http_outputs")


def _register_output_file(file_path: str) -> None:
    """Register a file path as allowed for HTTP serving."""
    resolved = str(Path(file_path).expanduser().resolve())
    _allowed_output_files.add(resolved)
    log.debug(f"Registered output file for serving: {resolved}")


def _is_file_allowed(file_path: str) -> bool:
    """Check if a file path is allowed for HTTP serving."""
    resolved = str(Path(file_path).expanduser().resolve())
    return resolved in _allowed_output_files


_VIDEO_WIDTH_PATTERN = re.compile(r"--video-width:\s*(\d+)\s*px", re.IGNORECASE)
_VIDEO_HEIGHT_PATTERN = re.compile(r"--video-height:\s*(\d+)\s*px", re.IGNORECASE)

def _sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", label.strip().lower())
    return cleaned or "input"

def _resolve_input_file(value: str, label: str) -> str:
    if not isinstance(value, str):
        return value
    candidate = value.strip()
    if candidate in _uploaded_to_comfy_files:
        return _uploaded_to_comfy_files[candidate]
    if candidate in _uploaded_input_files:
        comfy_ref = _upload_input_file(_uploaded_input_files[candidate], label)
        _uploaded_to_comfy_files[candidate] = comfy_ref
        return comfy_ref

    path_candidate = Path(candidate).expanduser()
    if path_candidate.exists():
        comfy_ref = _upload_input_file(str(path_candidate.resolve()), label)
        _uploaded_to_comfy_files[candidate] = comfy_ref
        return comfy_ref

    if candidate.startswith("http://") or candidate.startswith("https://"):
        comfy_ref = _upload_input_file(candidate, label)
        _uploaded_to_comfy_files[candidate] = comfy_ref
        return comfy_ref

    raise ValueError(
        f"{label} must be a local file path, remote URL, or a file_id resolvable "
    )


def _upload_input_file(source: str, label: str, upload_type: str = "input") -> str:
    local_path = _materialize_input_file(source, label)
    return _upload_local_file_to_comfy(
        local_path,
        upload_type=upload_type,
        remote_filename=f"{uuid.uuid4().hex}{Path(local_path).suffix or '.bin'}"
    )


def _materialize_input_file(source: str, label: str) -> str:
    cache_key = f"{label}:{source}"
    cached = _downloaded_input_files.get(cache_key)
    if cached and Path(cached).exists():
        return cached

    media_type = None
    source_path = Path(source).expanduser()
    if source_path.exists():
        return str(source_path.resolve())

    try:
        with urlopen(source, timeout=120) as response:  # nosec B310 - controlled server URL/path
            data = response.read()
            media_type = response.headers.get("Content-Type")
    except Exception as exc:
        raise ValueError(f"Failed to fetch {label} from {source}: {exc}") from exc

    suffix = ""
    if media_type:
        suffix = mimetypes.guess_extension(media_type.split(";", 1)[0].strip()) or ""
    if not suffix:
        suffix = Path(unquote(source)).suffix or ".bin"

    output_dir = Path("/tmp/mcp_video_http_inputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{_sanitize_label(label)}_{uuid.uuid4().hex}{suffix}"
    output_path.write_bytes(data)
    resolved = str(output_path.resolve())
    _downloaded_input_files[cache_key] = resolved
    return resolved


def _upload_local_file_to_comfy(
    local_path: str,
    upload_type: str = "input",
    remote_filename: Optional[str] = None
) -> str:
    path = Path(local_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"Input file not found for ComfyUI upload: {path}")

    boundary = f"----skillpilot-{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    file_content = path.read_bytes()

    body = bytearray()

    def _add_field(name: str, value: str) -> None:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    _add_field("overwrite", "true")
    _add_field("type", upload_type)
    upload_name = str(remote_filename or path.name).strip() or path.name

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="image"; filename="{upload_name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(file_content)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    raw = ""
    last_error = ""
    for endpoint in ("/upload/image", "/upload"):
        request = Request(
            f"{_comfy_server_base_url}{endpoint}",
            data=bytes(body),
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urlopen(request, timeout=120) as response:  # nosec B310 - controlled URL
                raw = response.read().decode("utf-8", errors="replace")
                last_error = ""
                break
        except Exception as exc:
            last_error = str(exc)
            continue

    if last_error:
        raise ValueError(f"Failed to upload input to ComfyUI: {last_error}")

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}

    name = str(payload.get("name") or payload.get("filename") or upload_name).strip()
    subfolder = str(payload.get("subfolder") or "").strip("/")
    uploaded_type = str(payload.get("type") or upload_type).strip("/")
    base_dir = ""
    if uploaded_type == "input":
        base_dir = _comfy_remote_input_dir
    elif uploaded_type == "output":
        base_dir = _comfy_remote_output_dir
    elif uploaded_type == "temp":
        base_dir = f"{_comfy_install_path}/temp" if _comfy_install_path else ""

    if subfolder:
        if base_dir:
            return f"{base_dir}/{subfolder}/{name}"
        return f"{subfolder}/{name}"
    if base_dir:
        return f"{base_dir}/{name}"
    return f"{uploaded_type}/{name}"


def _extract_comfy_file_parts(path_value: str, default_type: str = "output") -> tuple[str, str, str]:
    text = str(path_value or "").strip()
    if not text:
        raise ValueError("Empty ComfyUI file reference")
    if text.startswith("data:"):
        raise ValueError("Data URI cannot be downloaded from ComfyUI /view endpoint")
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        if parsed.path.rstrip("/") == "/view":
            query = parse_qs(parsed.query)
            filename = str((query.get("filename") or [""])[0]).strip()
            subfolder = str((query.get("subfolder") or [""])[0]).strip("/")
            file_type = str((query.get("type") or [default_type])[0]).strip() or default_type
            if not filename:
                raise ValueError(f"Missing filename in ComfyUI /view URL: {text}")
            return filename, subfolder, file_type
        raise ValueError(f"Unsupported URL for ComfyUI file download: {text}")

    normalized = text.replace("\\", "/")
    if _comfy_install_path:
        comfy_prefix = f"{_comfy_install_path.rstrip('/')}/"
        if normalized.startswith(comfy_prefix):
            normalized = normalized[len(comfy_prefix):]
    filename = Path(normalized).name
    if not filename:
        raise ValueError(f"Invalid ComfyUI file reference: {text}")

    parent = Path(normalized).parent.as_posix()
    file_type = default_type
    subfolder = ""

    if parent in {"input", "output", "temp"}:
        file_type = parent
    elif parent.startswith("input/") or parent.startswith("output/") or parent.startswith("temp/"):
        first, _, rest = parent.partition("/")
        file_type = first
        subfolder = rest
    elif parent not in {"", "."}:
        subfolder = parent

    return filename, subfolder, file_type

def _download_comfy_file(path_value: str, default_type: str = "output") -> str:
    filename, subfolder, file_type = _extract_comfy_file_parts(path_value, default_type=default_type)
    url = f"{_comfy_server_base_url}/view?{urlencode({'filename': filename, 'subfolder': subfolder, 'type': file_type})}"
    try:
        with urlopen(url, timeout=120) as response:  # nosec B310 - controlled URL
            file_data = response.read()
    except Exception as exc:
        raise ValueError(f"Failed to download ComfyUI file from {url}: {exc}") from exc

    ext = Path(filename).suffix or ".bin"
    _download_dir.mkdir(parents=True, exist_ok=True)
    local_path = _download_dir / f"{uuid.uuid4().hex}{ext}"
    local_path.write_bytes(file_data)
    _register_output_file(str(local_path))
    return str(local_path.resolve())


def _format_output(value: Any) -> Any:
    if isinstance(value, str):
        if value.startswith("data:"):
            return value
        if value.startswith("http://") or value.startswith("https://"):
            if _comfy_server_base_url and value.startswith(_comfy_server_base_url):
                return _download_comfy_file(value, default_type="output")
            return value
        path = Path(value).expanduser()
        if path.exists() and path.is_file():
            resolved = str(path.resolve())
            _register_output_file(resolved)
            return resolved
        return _download_comfy_file(value, default_type="output")
    if isinstance(value, list):
        return [_format_output(item) for item in value]
    if isinstance(value, dict):
        return {key: _format_output(item) for key, item in value.items()}
    return value


def _preview_text(value: str, limit: int = 200) -> str:
    """Return a safe preview of text for logging."""
    if not isinstance(value, str):
        return str(value)
    return value[:limit]


def _log_request(tool_name: str, extra: Dict | None = None) -> None:
    log.info(f"{tool_name} request received", extra=extra or {})


def _log_success(tool_name: str, extra: Dict | None = None) -> None:
    log.info(f"{tool_name} completed", extra=extra or {})


def _log_failure(tool_name: str, extra: Dict | None = None) -> None:
    log.exception(f"{tool_name} failed", extra=extra or {})


def _extract_viewport_dimensions(html_content: str) -> tuple[Optional[int], Optional[int]]:
    """Read CSS custom properties from HTML to determine viewport size."""
    width_match = _VIDEO_WIDTH_PATTERN.search(html_content)
    height_match = _VIDEO_HEIGHT_PATTERN.search(html_content)

    width = int(width_match.group(1)) if width_match else None
    height = int(height_match.group(1)) if height_match else None
    return width, height


def _validate_html_document(html_content: str) -> None:
    """Ensure HTML content has the basic structure needed for rendering."""
    lowered = html_content.lower()
    if "<html" not in lowered or "<body" not in lowered:
        raise ValueError("HTML file must contain <html> and <body> tags for rendering.")


def _has_js_function(html_content: str, function_name: str) -> bool:
    """Check whether HTML contains a JS function definition for the given name."""
    patterns = [
        rf"function\s+{function_name}\s*\(",
        rf"{function_name}\s*=\s*function\s*\(",
        rf"{function_name}\s*=\s*async\s*function\s*\(",
        rf"{function_name}\s*=\s*\(.*?\)\s*=>"
    ]
    return any(re.search(pattern, html_content, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _validate_html_animation(html_content: str) -> None:
    """Ensure HTML content has required structure and animation hooks."""
    _validate_html_document(html_content)

    for func in ("video_started", "video_ended"):
        if not _has_js_function(html_content, func):
            raise ValueError(
                f"HTML animation must define a JavaScript function named '{func}' "
                "so the recorder can detect playback state."
            )


def _require_local_file(path_str: str, label: str) -> Path:
    """Resolve input to a ComfyUI-accessible path reference."""
    path_value = _resolve_input_file(path_str, label)
    return Path(path_value)


async def _ensure_audio_within_limit(path: Path, label: str) -> None:
    """Apply the standard 3-minute cap used by GPU lipsync workflows."""
    duration = await get_audio_duration(str(path))
    if duration is not None and duration > MAX_LIPSYNC_AUDIO_SECONDS:
        raise WorkflowExecutionError(f"{label} exceeds maximum length of 3 minutes")


async def _ensure_audio_within_musetalk_limit(path: Path, label: str) -> None:
    """
    Apply a relaxed duration cap for the MuseTalk CLI lip-sync pipeline.

    MuseTalk can process longer audio than the default GPU workflows; the limit can be
    overridden via GPU_WORKER_MUSETALK_MAX_AUDIO_SECONDS (defaults to 1 hour).
    """
    duration = await get_audio_duration(str(path))
    if duration is None:
        return

    raw_value = str(os.getenv("GPU_WORKER_MUSETALK_MAX_AUDIO_SECONDS") or "").strip()
    max_seconds = float(DEFAULT_MUSETALK_MAX_AUDIO_SECONDS)
    if raw_value:
        try:
            max_seconds = float(raw_value)
        except ValueError as exc:
            raise WorkflowExecutionError(
                "Invalid GPU_WORKER_MUSETALK_MAX_AUDIO_SECONDS; expected a number of seconds"
            ) from exc

    if max_seconds <= 0:
        return

    if duration > max_seconds:
        raise WorkflowExecutionError(f"{label} exceeds maximum length of {max_seconds:.0f} seconds")


async def _convert_video_to_fps(video_path: str, target_fps: int = DEFAULT_VIDEO_FPS) -> str:
    """
    Normalize a video's frame rate using ffmpeg and return the converted path.

    This re-encodes the source clip to the target fps to keep downstream tools
    consistent (raw generator output is ~32fps).
    """
    input_path = Path(video_path).expanduser()
    if not input_path.exists():
        # Remote Comfy paths cannot be re-encoded locally.
        return video_path

    output_path = input_path.with_name(f"{input_path.stem}_{target_fps}fps{input_path.suffix}")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-r",
        str(target_fps),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_path)
    ]

    log.info(
        "Converting video FPS",
        extra={"input": str(input_path), "output": str(output_path), "fps": target_fps}
    )

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError as exc:
        raise WorkflowExecutionError("ffmpeg is required to normalize video FPS but was not found") from exc

    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        error_message = stderr.decode().strip() or stdout.decode().strip() or "ffmpeg conversion failed"
        raise WorkflowExecutionError(f"Failed to convert video to {target_fps}fps: {error_message}")

    return str(output_path)


async def _create_pingpong_video(video_path: str) -> str:
    """
    Create a pingpong (forward + reversed) version of a video using ffmpeg.
    """
    input_path = Path(video_path).expanduser()
    if not input_path.exists():
        # Remote Comfy paths cannot be transformed locally.
        return video_path

    output_path = input_path.with_name(f"{input_path.stem}_pingpong{input_path.suffix}")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-filter_complex",
        "[0:v]reverse[vrev];[0:v][vrev]concat=n=2:v=1:a=0,format=yuv420p[v]",
        "-map",
        "[v]",
        "-an",
        str(output_path)
    ]

    log.info(
        "Creating pingpong video",
        extra={"input": str(input_path), "output": str(output_path)}
    )

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError as exc:
        raise WorkflowExecutionError("ffmpeg is required to create a pingpong video but was not found") from exc

    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        error_message = stderr.decode().strip() or stdout.decode().strip() or "ffmpeg pingpong conversion failed"
        raise WorkflowExecutionError(f"Failed to create pingpong video: {error_message}")

    return str(output_path)


# ============================================================================
# GPU Workflow-Based Tools (11 tools)
# ============================================================================

@mcp.tool()
async def text_to_speech(
    text: str,
    emotion: str,
    emotion_sample: str = "",
    ref_voice: str = "",
    ref_emotion_voice: str = ""
) -> str:
    """
    Generate speech audio from text using TTS model.

    Args:
        text: The text content you want to convert into spoken words
        emotion: The emotional tone for the voice (neutral, happy, sad, angry, excited, calm, etc.)
        emotion_sample: Sentence showing the desired emotional delivery style (required)
        ref_voice: Audio file_id from /upload_file to use as reference for voice characteristics and timbre (required)
        ref_emotion_voice: Optional audio file_id from /upload_file to control emotional delivery;
                           when omitted/empty, defaults to ref_voice.

    Returns:
        Generated speech audio as a URL in MP3 format
    """
    try:
        request_extra = {
            "emotion": emotion,
            "text_preview": _preview_text(text)
        }
        _log_request("text_to_speech", request_extra)
        emotion_sample_value = str(emotion_sample or '').strip()
        if not emotion_sample_value:
            emotion_sample_value = str(text or '').strip()
        if not emotion_sample_value:
            raise ScriptExecutionError("emotion_sample is required for text_to_speech")

        ref_voice_value = str(ref_voice or '').strip()
        if not ref_voice_value:
            raise ScriptExecutionError("ref_voice is required for text_to_speech")
        ref_voice_value = _resolve_input_file(ref_voice_value, "ref_voice")
        ref_voice_path = Path(ref_voice_value).expanduser()

        ref_emotion_voice_value = str(ref_emotion_voice or '').strip()
        if ref_emotion_voice_value:
            ref_emotion_voice_value = _resolve_input_file(ref_emotion_voice_value, "ref_emotion_voice")
            ref_emotion_voice_path = Path(ref_emotion_voice_value).expanduser()
        else:
            ref_emotion_voice_path = ref_voice_path

        audio_file = await script_executor.generate_tts_audio(
            text=text,
            emotion=emotion,
            emotion_sample=emotion_sample_value,
            ref_voice=str(ref_voice_path),
            ref_emotion_voice=str(ref_emotion_voice_path)
        )
        _log_success("text_to_speech", {"audio_file": audio_file, **request_extra})
        return _format_output(audio_file)
    except ScriptExecutionError as e:
        _log_failure("text_to_speech", request_extra)
        raise Exception(f"Text-to-speech failed: {e}")


@mcp.tool()
async def text_segments_to_speech(
    segments: list[dict],
    ref_voice: str = ""
) -> list[str]:
    """
    Generate speech audio for multiple lines with per-line emotion control.

    Args:
        segments: List of dicts with fields text, emotion, and emotion_sample (all required);
                  Optionally include ref_emotion_voice per segment as a file_id from /upload_file;
                  when omitted/empty, defaults to ref_voice.
        ref_voice: Audio file_id from /upload_file to use as reference for voice characteristics and timbre

    Returns:
        List of generated speech audio segments as HTTP URLs (http://host:port/file/path) in WAV format

        Example:
        segments = [
            {
                "text": "Hi there! It is great to meet you.",
                "emotion": "happy",
                "emotion_sample": "I am so glad we finally get to meet in person!",
                "ref_emotion_voice": "file_id_from_upload"
            },
            {
                "text": "This is serious, so please pay attention.",
                "emotion": "serious",
                "emotion_sample": "This is serious, so please pay attention.",
                "ref_emotion_voice": "file_id_from_upload"
            }
        ]
        audio = await text_segments_to_speech(segments, ref_voice="file_id_from_upload")
    """
    try:
        request_extra = {
            "segments_count": len(segments) if segments else 0,
            "first_segment_preview": _preview_text(segments[0].get("text", "")) if segments else ""
        }
        _log_request("text_segments_to_speech", request_extra)
        if not segments:
            raise ScriptExecutionError("At least one segment is required for text_segments_to_speech")

        ref_voice_value = str(ref_voice or '').strip()
        if not ref_voice_value:
            raise ScriptExecutionError("ref_voice is required for text_segments_to_speech")
        ref_voice_value = _resolve_input_file(ref_voice_value, "ref_voice")
        ref_voice_path = Path(ref_voice_value).expanduser()

        validated_lines = []
        for index, line in enumerate(segments, start=1):
            if not isinstance(line, dict):
                raise ScriptExecutionError(
                    f"Line {index} must be an object with text, emotion, emotion_sample, and optional ref_emotion_voice"
                )

            text = str(line.get('text') or '').strip()
            emotion = str(line.get('emotion') or '').strip()
            emotion_sample = str(line.get('emotion_sample') or '').strip()

            if not text:
                raise ScriptExecutionError(f"Line {index} is missing text")
            if not emotion:
                raise ScriptExecutionError(f"Line {index} is missing emotion")
            if not emotion_sample:
                raise ScriptExecutionError(f"Line {index} is missing emotion_sample")

            ref_emotion_voice_value = str(line.get('ref_emotion_voice') or '').strip()
            if ref_emotion_voice_value:
                ref_emotion_voice_value = _resolve_input_file(
                    ref_emotion_voice_value,
                    f"ref_emotion_voice line {index}"
                )
                ref_emotion_voice_path = Path(ref_emotion_voice_value).expanduser()
            else:
                ref_emotion_voice_path = ref_voice_path

            validated_lines.append({
                'text': text,
                'emotion': emotion,
                'emotion_sample': emotion_sample,
                'ref_emotion_voice': str(ref_emotion_voice_path)
            })

        audio_files = await script_executor.generate_tts_lines_audio(
            lines=validated_lines,
            ref_voice=str(ref_voice_path)
        )
        _log_success("text_segments_to_speech", {"audio_files": audio_files, **request_extra})
        return _format_output(audio_files)
    except ScriptExecutionError as e:
        _log_failure("text_segments_to_speech", request_extra)
        raise Exception(f"Text-segments-to-speech failed: {e}")


@mcp.tool()
async def text_to_song(
    lyrics: str,
    ref_voice: Optional[str] = None
) -> str:
    """
    Generate singing audio from lyrics with musical vocal delivery.

    Args:
        lyrics: The song lyrics to be sung (can include multiple verses and chorus)
        ref_voice: Required audio file_id, local file path, or remote URL to use as reference for the singing voice timbre and characteristics

    Returns:
        Generated singing audio as a URL in MP3 format
    """
    try:
        request_extra = {
            "lyrics_preview": _preview_text(lyrics),
            "ref_voice_provided": bool(ref_voice)
        }
        _log_request("text_to_song", request_extra)
        ref_voice_value = str(ref_voice or "").strip()
        if not ref_voice_value:
            raise ScriptExecutionError("ref_voice is required for text_to_song")
        ref_voice = _resolve_input_file(ref_voice_value, "ref_voice")

        lyrics = lyrics.strip()
        if lyrics[0] != '[':
            raise ScriptExecutionError("Lyrics must start with a structure flag like [verse], [chorus], etc.")

        audio_file = await script_executor.generate_song_audio(
            lyrics=lyrics,
            ref_voice=ref_voice
        )
        _log_success("text_to_song", {"audio_file": audio_file, **request_extra})
        return _format_output(audio_file)
    except ScriptExecutionError as e:
        _log_failure("text_to_song", request_extra)
        raise Exception(f"Text-to-song failed: {e}")

@mcp.tool()
async def text_to_image(
    prompt: str,
    width: int = 624,
    height: int = 624
) -> str:
    """
    Generate an image from a text description using AI image generation.

    Args:
        prompt: Detailed description of the image you want to create (describe subjects, style, colors, composition, mood, etc.)
        width: Width of the generated image in pixels (default: 624)
        height: Height of the generated image in pixels (default: 624)

    Returns:
        Generated image as a URL in PNG or JPEG format
    """
    try:
        request_extra = {
            "width": width,
            "height": height,
            "prompt_preview": _preview_text(prompt)
        }
        _log_request("text_to_image", request_extra)
        # Prepare task input
        task_input = {
            'image_prompt': prompt,
            'width': width,
            'height': height,
            'ratio': 'square'
        }

        # Execute workflow
        result = await workflow_executor.execute_workflow(
            workflow_id='text-to-image',
            task_input=task_input,
            downloaded_files={},
            task_type='text-to-image'
        )

        # Return image path
        image_path = result.get('image_url')
        if not image_path:
            raise WorkflowExecutionError('No image output from workflow')

        _log_success("text_to_image", {"image_path": image_path, **request_extra})
        return _format_output(image_path)
    except WorkflowExecutionError as e:
        _log_failure("text_to_image", request_extra)
        raise Exception(f"Text-to-image failed: {e}")


@mcp.tool()
async def text_to_video(
    prompt: str,
    width: int = 768,
    height: int = 512
) -> str:
    """
    Generate a video clip from a text description using AI video generation.

    Args:
        prompt: Detailed description of the video scene you want to create (describe action, movement, subjects, environment, camera motion, etc.)
        width: Width of the generated video in pixels (default: 768)
        height: Height of the generated video in pixels (default: 512)

    Returns:
        Generated video as a URL in MP4 format, no audio
    """
    try:
        request_extra = {
            "width": width,
            "height": height,
            "prompt_preview": _preview_text(prompt)
        }
        _log_request("text_to_video", request_extra)
        # Prepare task input
        task_input = {
            'video_prompt': prompt,
            'width': width,
            'height': height
        }

        # Execute workflow
        result = await workflow_executor.execute_workflow(
            workflow_id='text-to-video',
            task_input=task_input,
            downloaded_files={},
            task_type='text-to-video'
        )

        # Return raw video path
        video_path = result.get('upscaled_video_url')
        if not video_path:
            raise WorkflowExecutionError('No video output from workflow')

        video_path = await _convert_video_to_fps(video_path, DEFAULT_VIDEO_FPS)
        _log_success("text_to_video", {"video_path": video_path, **request_extra})
        return _format_output(video_path)
    except WorkflowExecutionError as e:
        _log_failure("text_to_video", request_extra)
        raise Exception(f"Text-to-video failed: {e}")


@mcp.tool()
async def image_to_image(
    prompt: str,
    image_file: str
) -> str:
    """
    Modify or transform an existing image based on text instructions using AI.

    Args:
        prompt: Description of how you want to modify the image (e.g., "add flowers", "change to winter scene", "make it look vintage", etc.)
        image_file: Image file_id from /upload_file to modify (supports PNG, JPEG formats)

    Returns:
        Modified image as a URL in PNG or JPEG format
    """
    try:
        request_extra = {
            "prompt_preview": _preview_text(prompt),
            "image_file": image_file
        }
        _log_request("image_to_image", request_extra)
        image_file = _resolve_input_file(image_file, "image_file")

        # Prepare task input
        task_input = {
            'image_prompt': prompt
        }

        # Prepare downloaded files
        downloaded_files = {
            '{{source_image}}': image_file
        }

        # Execute workflow
        result = await workflow_executor.execute_workflow(
            workflow_id='image-to-image',
            task_input=task_input,
            downloaded_files=downloaded_files,
            task_type='image-to-image'
        )

        # Return image path
        image_path = result.get('image_url')
        if not image_path:
            raise WorkflowExecutionError('No image output from workflow')

        _log_success("image_to_image", {"image_path": image_path, **request_extra})
        return _format_output(image_path)
    except WorkflowExecutionError as e:
        _log_failure("image_to_image", request_extra)
        raise Exception(f"Image-to-image failed: {e}")


@mcp.tool()
async def image_to_video(
    prompt: str,
    image_file: str,
    width: int = 768,
    height: int = 512
) -> str:
    """
    Animate a static image into a video using AI to add motion and life.

    Args:
        prompt: Description of how the image should be animated (e.g., "camera slowly zooms in", "trees sway in the wind", "person walks forward", etc.)
        image_file: Static image file_id from /upload_file to animate (supports PNG, JPEG formats)
        width: Width of the generated video in pixels (default: 768)
        height: Height of the generated video in pixels (default: 512)

    Returns:
        Generated animated video as a URL in MP4 format, no audio
    """
    try:
        request_extra = {
            "prompt_preview": _preview_text(prompt),
            "image_file": image_file,
            "width": width,
            "height": height
        }
        _log_request("image_to_video", request_extra)
        image_file = _resolve_input_file(image_file, "image_file")

        # Prepare task input
        task_input = {
            'video_prompt': prompt,
            'width': width,
            'height': height
        }

        # Prepare downloaded files
        downloaded_files = {
            '{{source_image}}': image_file
        }

        # Execute workflow
        result = await workflow_executor.execute_workflow(
            workflow_id='image-to-video',
            task_input=task_input,
            downloaded_files=downloaded_files,
            task_type='image-to-video'
        )

        # Return raw video path
        video_path = result.get('upscaled_video_url')
        if not video_path:
            raise WorkflowExecutionError('No video output from workflow')

        video_path = await _convert_video_to_fps(video_path, DEFAULT_VIDEO_FPS)
        _log_success("image_to_video", {"video_path": video_path, **request_extra})
        return _format_output(video_path)
    except WorkflowExecutionError as e:
        _log_failure("image_to_video", request_extra)
        raise Exception(f"Image-to-video failed: {e}")


@mcp.tool()
async def flf_to_video(
    prompt: str,
    first_frame_image: str,
    last_frame_image: str,
    width: int = 768,
    height: int = 512
) -> str:
    """
    Create a video by interpolating motion between two images (first and last frame).

    Args:
        prompt: Description of the transition and motion between the frames (e.g., "smooth transition", "person walks from position A to B", "camera pans", etc.)
        first_frame_image: Starting frame image file_id from /upload_file
        last_frame_image: Ending frame image file_id from /upload_file
        width: Width of the generated video in pixels (default: 768)
        height: Height of the generated video in pixels (default: 512)

    Returns:
        Generated video as a URL interpolating between the two frames in MP4 format, no audio
    """
    try:
        request_extra = {
            "prompt_preview": _preview_text(prompt),
            "first_frame_image": first_frame_image,
            "last_frame_image": last_frame_image,
            "width": width,
            "height": height
        }
        _log_request("flf_to_video", request_extra)
        first_frame_image = _resolve_input_file(first_frame_image, "first_frame_image")
        last_frame_image = _resolve_input_file(last_frame_image, "last_frame_image")

        # Prepare task input
        task_input = {
            'video_prompt': prompt,
            'width': width,
            'height': height
        }

        # Prepare downloaded files
        downloaded_files = {
            '{{source_image_1}}': first_frame_image,
            '{{source_image_2}}': last_frame_image
        }

        # Execute workflow
        result = await workflow_executor.execute_workflow(
            workflow_id='flf_to_video',
            task_input=task_input,
            downloaded_files=downloaded_files,
            task_type='flf_to_video'
        )

        # Return raw video path
        video_path = result.get('upscaled_video_url')
        if not video_path:
            raise WorkflowExecutionError('No video output from workflow')

        _log_success("flf_to_video", {"video_path": video_path, **request_extra})
        return _format_output(video_path)
    except WorkflowExecutionError as e:
        _log_failure("flf_to_video", request_extra)
        raise Exception(f"FLF-to-video failed: {e}")


@mcp.tool()
async def video_upscale(
    video_file: str
) -> str:
    """
    Upscale and enhance a video using the ComfyUI upscale workflow.

    Args:
        video_file: Video file_id from /upload_file to upscale.

    Returns:
        Upscaled video as a URL in MP4 format.
    """
    video_path = _require_local_file(video_file, "Video file")
    request_extra = {"video_file": str(video_path)}

    try:
        _log_request("video_upscale", request_extra)
        result = await workflow_executor.execute_workflow(
            workflow_id='upscale-video',
            task_input={},
            downloaded_files={'{{source_video}}': str(video_path)},
            task_type='upscale-video'
        )

        upscaled_video = result.get('upscaled_video_url')
        if not upscaled_video:
            raise WorkflowExecutionError('No upscaled video output from workflow')

        _log_success("video_upscale", {"video_path": upscaled_video, **request_extra})
        return _format_output(upscaled_video)
    except WorkflowExecutionError as e:
        _log_failure("video_upscale", request_extra)
        raise Exception(f"Video upscale failed: {e}")


@mcp.tool()
async def image_to_talk_video(
    prompt: str,
    image_file: str,
    audio_file: str,
    width: int = 448,
    height: int = 448,
    upscale: bool = True
) -> str:
    """
    Create a single-person talking or singing video from a face image synchronized with audio.

    Args:
        prompt: Optional guidance for the video generation style (e.g., "natural expression", "animated talking", "expressive singing", "energetic performance", etc.)
        image_file: Face image file_id from /upload_file containing a face that will appear to speak or sing (headshot or portrait works best)
        audio_file: Speech or singing audio file_id from /upload_file that the face will be synchronized to (supports MP3, WAV formats)
        width: Width of the generated video in pixels (default: 448)
        height: Height of the generated video in pixels (default: 448)
        upscale: When true (default), automatically upscale the generated video before returning

    Returns:
        Generated lip-synced video as a URL in MP4 format with audio, max 3 minutes
    """
    try:
        request_extra = {
            "prompt_preview": _preview_text(prompt),
            "image_file": image_file,
            "audio_file": audio_file,
            "width": width,
            "height": height,
            "upscale": upscale
        }
        _log_request("image_to_talk_video", request_extra)
        image_file = _resolve_input_file(image_file, "image_file")
        audio_file = _resolve_input_file(audio_file, "audio_file")

        # Determine clip length to bound frame count
        audio_duration = await get_audio_duration(audio_file)
        max_frames = 4500
        if audio_duration is not None and audio_duration > 3 * 60:
            raise WorkflowExecutionError("Audio duration exceeds maximum of 3 minutes")
  

        # Prepare task input
        task_input = {
            'video_prompt': prompt,
            'width': width,
            'height': height,
            'max_frames': max_frames
        }

        # Prepare downloaded files
        downloaded_files = {
            '{{source_image}}': image_file,
            '{{audio_file}}': audio_file
        }

        # Execute workflow
        result = await workflow_executor.execute_workflow(
            workflow_id='image-to-talk-video',
            task_input=task_input,
            downloaded_files=downloaded_files,
            task_type='image-to-talk-video'
        )

        # Return raw video path
        video_path = result.get('raw_video_url')
        if not video_path:
            raise WorkflowExecutionError('No video output from workflow')

        if upscale:
            video_path = await video_upscale(video_path)

        _log_success("image_to_talk_video", {"video_path": video_path, **request_extra})
        return _format_output(video_path)
    except WorkflowExecutionError as e:
        _log_failure("image_to_talk_video", request_extra)
        raise Exception(f"Image-to-talk-video failed: {e}")


@mcp.tool()
async def video_to_talk_video(
    prompt: str,
    video_file: str,
    audio_file: str,
    width: int = 448,
    height: int = 448,
    upscale: bool = True,
    pingpong: bool = True
) -> str:
    """
    Create a talking or singing video from an existing clip synchronized with audio.

    Args:
        prompt: Optional guidance for the video generation style (e.g., "natural expression", "animated talking", "expressive singing", "energetic performance", etc.)
        video_file: Source video file_id from /upload_file whose subject will be reanimated to match the audio.
        audio_file: Speech or singing audio file_id from /upload_file that the face will be synchronized to (supports MP3, WAV formats)
        width: Width of the generated video in pixels (default: 448)
        height: Height of the generated video in pixels (default: 448)
        upscale: When true (default), automatically upscale the generated video before returning
        pingpong: When true (default), mirror the input clip into a forward+reverse pingpong loop before processing

    Returns:
        Generated lip-synced video as a URL in MP4 format with audio, max 3 minutes
    """
    request_extra = {
        "prompt_preview": _preview_text(prompt),
        "video_file": video_file,
        "audio_file": audio_file,
        "width": width,
        "height": height,
        "upscale": upscale,
        "pingpong": pingpong
    }
    _log_request("video_to_talk_video", request_extra)

    try:
        video_file = _resolve_input_file(video_file, "video_file")
        audio_file = _resolve_input_file(audio_file, "audio_file")
        video_path = _require_local_file(video_file, "Video file")
        audio_path = _require_local_file(audio_file, "Audio file")

        audio_duration = await get_audio_duration(str(audio_path))
        max_frames = 4500
        if audio_duration is not None and audio_duration > 3 * 60:
            raise WorkflowExecutionError("Audio duration exceeds maximum of 3 minutes")

        processed_video_path = str(video_path)
        if pingpong:
            processed_video_path = await _create_pingpong_video(str(video_path))
            request_extra["processed_video_file"] = processed_video_path

        task_input = {
            'video_prompt': prompt,
            'width': width,
            'height': height,
            'max_frames': max_frames
        }

        downloaded_files = {
            '{{source_video}}': processed_video_path,
            '{{ref_audio}}': str(audio_path)
        }

        result = await workflow_executor.execute_workflow(
            workflow_id='video-to-talk-video',
            task_input=task_input,
            downloaded_files=downloaded_files,
            task_type='video-to-talk-video'
        )

        video_path = result.get('raw_video_url')
        if not video_path:
            raise WorkflowExecutionError('No video output from workflow')

        if upscale:
            video_path = await video_upscale(video_path)

        _log_success("video_to_talk_video", {"video_path": video_path, **request_extra})
        return _format_output(video_path)
    except WorkflowExecutionError as e:
        _log_failure("video_to_talk_video", request_extra)
        raise Exception(f"Video-to-talk-video failed: {e}")


@mcp.tool()
async def image_to_dialog_video(
    prompt: str,
    image_file: str,
    audio_file_one: str,
    audio_file_two: str,
    width: int = 448,
    height: int = 448,
    reverse_order: bool = False,
    max_frames: int = 450
) -> Dict[str, str]:
    """
    Generate two synchronized talking-head videos (one per dialog role) from a single portrait.

    Args:
        prompt: Required guidance for the animation style and expressions.
        image_file: Image file_id from /upload_file that will be re-animated for both roles.
        audio_file_one: Audio file_id from /upload_file for the first role (left/top speaker by default).
        audio_file_two: Audio file_id from /upload_file for the second role.
        width: Width of each generated video frame.
        height: Height of each generated video frame.
        reverse_order: Swap which audio drives the first/second split outputs (mirrors GPU worker toggle).
        max_frames: Maximum number of frames to render before stopping.

    Returns:
        Dictionary with `split_one_video` and `split_two_video` as HTTP URLs (http://host:port/file/path).
    """
    request_extra = {
        "prompt_preview": _preview_text(prompt),
        "image_file": image_file,
        "audio_file_one": audio_file_one,
        "audio_file_two": audio_file_two,
        "width": width,
        "height": height,
        "reverse_order": reverse_order,
        "max_frames": max_frames
    }
    _log_request("image_to_dialog_video", request_extra)

    prompt_value = (prompt or '').strip()
    if not prompt_value:
        raise WorkflowExecutionError("Prompt is required for dialog video generation")

    image_file = _resolve_input_file(image_file, "image_file")
    audio_file_one = _resolve_input_file(audio_file_one, "audio_file_one")
    audio_file_two = _resolve_input_file(audio_file_two, "audio_file_two")
    image_path = _require_local_file(image_file, "Image file")
    audio_one_path = _require_local_file(audio_file_one, "Dialog audio file #1")
    audio_two_path = _require_local_file(audio_file_two, "Dialog audio file #2")

    await _ensure_audio_within_limit(audio_one_path, "Dialog audio file #1")
    await _ensure_audio_within_limit(audio_two_path, "Dialog audio file #2")

    task_input = {
        'video_prompt': prompt_value,
        'width': width,
        'height': height,
        'max_frames': max_frames,
        'reverse_order': 'true' if reverse_order else 'false'
    }

    downloaded_files = {
        '{{source_image}}': str(image_path),
        '{{audio_file1}}': str(audio_one_path),
        '{{audio_file2}}': str(audio_two_path)
    }

    try:
        result = await workflow_executor.execute_workflow(
            workflow_id='image-to-dialog-split-video',
            task_input=task_input,
            downloaded_files=downloaded_files,
            task_type='image-to-dialog-video'
        )
    except WorkflowExecutionError as e:
        _log_failure("image_to_dialog_video", request_extra)
        raise Exception(f"Image-to-dialog-video failed: {e}")

    split_one = result.get('raw_split_1_video_url')
    split_two = result.get('raw_split_2_video_url')
    if not split_one or not split_two:
        raise WorkflowExecutionError("Dialog workflow did not return both split video outputs")

    _log_success(
        "image_to_dialog_video",
        {
            "split_one_video": split_one,
            "split_two_video": split_two,
            **request_extra
        }
    )
    return _format_output({
        'split_one_video': split_one,
        'split_two_video': split_two
    })


@mcp.tool()
async def video_lipsync(
    audio_file: str,
    video_file: str,
    label: Optional[str] = None,
    pingpong: bool = True
) -> str:
    """
    Run the MuseTalk lip-sync CLI to align a reference video with a new audio track.

    Args:
        audio_file: Speech or singing audio file_id from /upload_file to drive the lip-sync.
        video_file: Input video file_id from /upload_file whose lip movements should be updated.
        label: Optional identifier that is forwarded to the MuseTalk CLI for logging.
        pingpong: When true (default), mirror the input clip into a forward+reverse pingpong loop before lip-syncing.

    Returns:
        Lip-synced video as a URL produced by MuseTalk.
    """
    audio_file = _resolve_input_file(audio_file, "audio_file")
    video_file = _resolve_input_file(video_file, "video_file")
    audio_path = _require_local_file(audio_file, "Audio file")
    video_path = _require_local_file(video_file, "Video file")
    await _ensure_audio_within_musetalk_limit(audio_path, "Audio file")

    request_extra = {
        "audio_file": str(audio_path),
        "video_file": str(video_path),
        "label": label,
        "pingpong": pingpong
    }
    processed_video_path = str(video_path)

    try:
        if pingpong:
            processed_video_path = await _create_pingpong_video(str(video_path))
            request_extra["processed_video_file"] = processed_video_path

        _log_request("video_lipsync", request_extra)
        output = await script_executor.run_musetalk_lipsync(
            audio_file=str(audio_path),
            video_file=processed_video_path,
            label=label
        )
        _log_success("video_lipsync", {"output_file": output, **request_extra})
        return _format_output(output)
    except (ScriptExecutionError, WorkflowExecutionError) as exc:
        _log_failure("video_lipsync", request_extra)
        raise Exception(f"Video lip-sync failed: {exc}") from exc


# ============================================================================
# HTML/CSS Animation Tools
# ============================================================================

@mcp.tool()
async def html5_video_clip(
    html_file: str,
    width: int,
    height: int,
    animate_time: float = 10.0
) -> str:
    """
    Render an HTML/CSS/JS animation into an MP4 clip using a headless browser.

    Args:
        html_file: HTML file_id from /upload_file that defines video_started()/video_ended() helpers.
        width: Viewport width (px) for the recorded clip.
        height: Viewport height (px) for the recorded clip.
        animate_time: Maximum duration in seconds to wait for the animation to finish.

    Returns:
        Recorded video clip as a URL in MP4 format.

    Example HTML snippet:
    ```html
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        :root { --video-width: 1080px; --video-height: 1920px; }
        body { width: var(--video-width); height: var(--video-height); margin: 0;
               display: flex; align-items: center; justify-content: center;
               font-family: 'Inter', sans-serif; background: #020617; color: white; }
        .card { opacity: 0; font-size: 64px; transition: opacity 1s ease; }
        body.ready .card { opacity: 1; }
      </style>
    </head>
    <body>
      <div class="card">Launch Day</div>
      <script>
        let started = false; let ended = false;
        function video_started() {
          if (!started) {
            started = true;
            document.body.classList.add('ready');
            setTimeout(() => { ended = true; }, 4000);
          }
          return started;
        }
        function video_ended() { return ended; }
        setTimeout(video_started, 200);
      </script>
    </body>
    </html>
    ```
    """
    html_file = _materialize_input_file(html_file, "html_file")
    source_path = Path(html_file).expanduser()
    if not source_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file}")

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive integers representing pixels")

    try:
        duration = float(animate_time)
    except (TypeError, ValueError):
        raise ValueError("animate_time must be a positive number of seconds")

    if duration <= 0:
        raise ValueError("animate_time must be greater than zero")

    try:
        html_content = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("HTML file must be UTF-8 encoded") from exc

    _validate_html_animation(html_content)

    # Allow CSS hints to override viewport when available
    css_width, css_height = _extract_viewport_dimensions(html_content)
    view_width = css_width or width
    view_height = css_height or height
    is_horizontal = view_width >= view_height

    output_path = f"/tmp/html5_animation_{uuid.uuid4()}.mp4"
    # Add buffer for browser start/stop and transcode time so long clips do not time out prematurely
    timeout_window = max(duration * 2.5, duration + 10)
    request_extra = {
        "html_file": str(source_path),
        "width": width,
        "height": height,
        "viewport_width": view_width,
        "viewport_height": view_height,
        "animate_time": duration
    }

    try:
        _log_request("html5_video_clip", request_extra)
        video_path = await asyncio.wait_for(
            record_screen(
                html_code=html_content,
                output_file=output_path,
                duration=duration,
                isHorizontal=is_horizontal,
                view_width=view_width,
                view_height=view_height
            ),
            timeout=timeout_window
        )
    except asyncio.TimeoutError as exc:
        _log_failure("html5_video_clip", request_extra)
        raise TimeoutError(
            f"Timed out recording HTML animation (>{timeout_window:.1f}s). "
            "Check video_started()/video_ended() logic."
        ) from exc
    except Exception as exc:
        _log_failure("html5_video_clip", request_extra)
        raise Exception(f"Failed to create HTML5 video clip: {exc}") from exc
    _log_success("html5_video_clip", {"video_path": video_path, **request_extra})
    return _format_output(video_path)


@mcp.tool()
async def html_image(
    html_file: str,
    width: int,
    height: int,
    transparent: bool = False
) -> str:
    """
    Create static html/css style image, transparent text overlay for video, and video thumbnail image.

    Args:
        html_file: HTML file_id from /upload_file to render.
        width: Fallback viewport width (px) if CSS variables are not present.
        height: Fallback viewport height (px) if CSS variables are not present.
        transparent: When true, omit the page background for a transparent overlay image.

    Returns:
        Captured image as a URL in PNG format.
    """
    html_file = _materialize_input_file(html_file, "html_file")
    source_path = Path(html_file).expanduser()
    if not source_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file}")

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive integers representing pixels")

    if not isinstance(transparent, bool):
        raise ValueError("transparent must be a boolean flag")

    try:
        html_content = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("HTML file must be UTF-8 encoded") from exc

    _validate_html_document(html_content)

    css_width, css_height = _extract_viewport_dimensions(html_content)
    view_width = css_width or width
    view_height = css_height or height
    is_horizontal = view_width >= view_height

    request_extra = {
        "html_file": str(source_path),
        "width": width,
        "height": height,
        "viewport_width": view_width,
        "viewport_height": view_height,
        "transparent": transparent
    }
    _log_request("html_image", request_extra)

    try:
        image_path = await capture_image(
            html_code=html_content,
            isHorizontal=is_horizontal,
            view_width=view_width,
            view_height=view_height,
            omitBackground=transparent,
            timeout=20,
            retries=3
        )
        if not image_path:
            raise RuntimeError("Playwright returned no image path")
    except Exception as exc:
        _log_failure("html_image", request_extra)
        raise Exception(f"Failed to render HTML image: {exc}") from exc

    _log_success("html_image", {"image_path": image_path, **request_extra})
    return _format_output(image_path)


@mcp.tool()
async def image_analysis(
    prompt: str,
    image_file: str,
    max_tokens: int = 512
) -> str:
    """
    Analyze an image using AI vision model to answer questions or provide descriptions.

    Args:
        prompt: Your question or request about the image (e.g., "What objects are in this image?", "Describe the scene", "What color is the car?", etc.)
        image_file: Image file_id from /upload_file to analyze (supports PNG, JPEG formats)
        max_tokens: Maximum length of the analysis response in tokens (default: 512)

    Returns:
        Text response with the image analysis or answer to your question
    """
    try:
        request_extra = {
            "prompt_preview": _preview_text(prompt),
            "image_file": image_file,
            "max_tokens": max_tokens
        }
        _log_request("image_analysis", request_extra)
        image_file = _resolve_input_file(image_file, "image_file")

        # Run analysis
        analysis = await script_executor.analyze_image(
            prompt=prompt,
            image_file=image_file,
            max_tokens=max_tokens
        )

        _log_success("image_analysis", {"analysis_preview": _preview_text(analysis), **request_extra})
        return analysis
    except ScriptExecutionError as e:
        _log_failure("image_analysis", request_extra)
        raise Exception(f"Image analysis failed: {e}")


@mcp.tool()
async def video_analysis(
    prompt: str,
    video_file: str,
    frame_step: int = 16,
    max_frames: int = -1,
    max_tokens: int = 2048
) -> str:
    """
    Analyze a video using AI vision model to answer questions or provide descriptions.

    Args:
        prompt: Your question or request about the video (e.g., "What happens in this video?", "Describe the actions", "Count how many people appear", etc.)
        video_file: Video file_id from /upload_file to analyze (supports MP4, AVI, MOV formats)
        frame_step: How many frames to skip between samples (1=analyze every frame, 16=analyze every 16th frame for faster processing)
        max_frames: Maximum number of frames to analyze (-1 means analyze all sampled frames)
        max_tokens: Maximum length of the analysis response in tokens (default: 2048)

    Returns:
        Text response with the video analysis or answer to your question
    """
    try:
        request_extra = {
            "prompt_preview": _preview_text(prompt),
            "video_file": video_file,
            "frame_step": frame_step,
            "max_frames": max_frames,
            "max_tokens": max_tokens
        }
        _log_request("video_analysis", request_extra)
        video_file = _resolve_input_file(video_file, "video_file")

        # Run analysis
        analysis = await script_executor.analyze_video(
            prompt=prompt,
            video_file=video_file,
            frame_step=frame_step,
            max_frames=max_frames,
            max_tokens=max_tokens
        )

        _log_success("video_analysis", {"analysis_preview": _preview_text(analysis), **request_extra})
        return analysis
    except ScriptExecutionError as e:
        _log_failure("video_analysis", request_extra)
        raise Exception(f"Video analysis failed: {e}")


@mcp.tool()
async def audio_segments(
    audio_file: str,
    language: str = "en"
) -> list:
    """
    Transcribe audio and return segments with timing information for understanding scene transitions.

    This tool helps AI agents understand the timing and structure of audio content, which is crucial
    for video editing tasks such as:
    - Splitting narration into natural scene segments based on speech pauses
    - Synchronizing video transitions with audio timing
    - Aligning visual content with spoken content
    - Creating captions or subtitles with accurate timestamps
    - Planning video scene cuts at natural speech boundaries

    Args:
        audio_file: Audio file_id from /upload_file to transcribe (supports MP3, WAV, M4A, etc.)
        language: Language code for transcription (default: "en"). Common codes: en, es, fr, de, it, pt, ru, ja, zh, ko
        use_fp16: Use FP16 precision for faster processing (default: True, requires CUDA)

    Returns:
        List of segments, each containing:
        - text: The transcribed text for this segment
        - start: Start time of the segment in seconds (float)
        - end: End time of the segment in seconds (float)
        - words: List of word-level timestamps (each with 'word', 'start', 'end')

    Example return value:
        [
            {
                "text": "Hello and welcome to this tutorial.",
                "start": 0.5,
                "end": 3.2,
                "words": [
                    {"word": "Hello", "start": 0.5, "end": 0.9},
                    {"word": "and", "start": 1.0, "end": 1.1},
                    ...
                ]
            },
            {
                "text": "Today we'll be learning about video editing.",
                "start": 3.5,
                "end": 6.8,
                "words": [...]
            }
        ]

    Use cases:
        - Find natural pauses between sentences to plan scene transitions
        - Synchronize video clips with specific parts of narration
        - Create dynamic captions that appear word-by-word
        - Split long videos into chapters based on topic changes
        - Identify timing for background music to avoid overlapping with speech
    """
    try:
        request_extra = {
            "audio_file": audio_file,
            "language": language
        }
        _log_request("audio_segments", request_extra)
        audio_file = _resolve_input_file(audio_file, "audio_file")

        use_fp16 = True

        # Run transcription
        segments = await script_executor.transcribe_audio(
            audio_file=audio_file,
            language=language,
            use_fp16=use_fp16
        )

        _log_success("audio_segments", {"segments_count": len(segments), **request_extra})
        return segments
    except ScriptExecutionError as e:
        _log_failure("audio_segments", request_extra)
        raise Exception(f"Audio transcription failed: {e}")


@mcp.tool()
async def extract_vocals(
    audio_file: str
) -> str:
    """
    Extract vocals from an audio file using Demucs source separation.

    This tool uses AI to separate vocals from background music and other sounds in an audio file.
    Perfect for:
    - Creating karaoke/instrumental versions by removing vocals
    - Isolating vocal tracks for remixing or analysis
    - Cleaning up dialogue with background music
    - Preparing audio for vocal processing or lip-sync
    - Extracting singing or speech from mixed audio

    Args:
        audio_file: Audio file_id from /upload_file (supports MP3, WAV, FLAC, M4A, etc.)

    Returns:
        Extracted vocals audio as a URL in WAV format

    Note:
        This process may take a few minutes depending on the audio length and system performance.
        The returned file contains only the vocal parts of the audio.
    """
    try:
        request_extra = {
            "audio_file": audio_file
        }
        _log_request("extract_vocals", request_extra)

        audio_file = _resolve_input_file(audio_file, "audio_file")
        audio_path = Path(audio_file).expanduser()

        # Get the demucs CLI script path from environment
        demucs_script = os.getenv('GPU_WORKER_DEMUCS_CLI')
        if not demucs_script:
            raise ScriptExecutionError('GPU_WORKER_DEMUCS_CLI environment variable not set')

        # Prepare payload
        payload = {
            'audio_file': str(audio_path),
            'output_dir': _comfy_remote_output_dir
        }

        # Execute the demucs script
        result = await script_executor.run_structured_script(
            script_path=demucs_script,
            payload=payload,
            description="Demucs vocal extraction",
            output_tag='json-output'
        )

        # Extract vocals file from result
        vocals_file = result.get('vocals_file')
        if not vocals_file:
            raise ScriptExecutionError('Demucs script returned no vocals file')

        _log_success("extract_vocals", {"vocals_file": vocals_file, **request_extra})
        return _format_output(vocals_file)
    except ScriptExecutionError as e:
        _log_failure("extract_vocals", request_extra)
        raise Exception(f"Vocal extraction failed: {e}")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    _load_env_from_mcp_config()
    _ensure_required_environment()
    _comfy_install_path = str(os.getenv("COMFYUI_INSTALL_PATH") or "").rstrip("/")
    _comfy_remote_input_dir = f"{_comfy_install_path}/input"
    _comfy_remote_output_dir = f"{_comfy_install_path}/output"
    _comfy_server_base_url = (os.getenv("COMFYUI_SERVER_ADDRESS") or "").rstrip("/")
    log.info("Starting media MCP server with stdio transport")
    mcp.run(transport="stdio")
