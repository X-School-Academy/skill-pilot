import base64
import asyncio
import json
import os
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from llm_service import get_tts_provider
from settings import PROJECT_DIR, logger


def _http_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float = 60.0) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=body, method="POST", headers={"Content-Type": "application/json", **headers})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            return json.loads(data)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"TTS provider HTTP error: {detail or exc.reason}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"TTS provider network error: {exc.reason}") from exc


def _write_wav(path: Path, pcm_bytes: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_bytes)


def _extract_mcp_text_content(payload: Any) -> Optional[str]:
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


def _normalize_media_mcp_input_reference(value: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return candidate

    if candidate.startswith(("http://", "https://")):
        return candidate

    expanded = Path(candidate).expanduser()
    if expanded.is_absolute():
        return str(expanded)

    project_relative = (PROJECT_DIR / expanded).resolve()
    if project_relative.exists():
        return str(project_relative)

    # Preserve non-path identifiers such as uploaded file ids.
    return candidate


def _skill_pilot_tts(text: str, provider: Dict[str, Any], voice: Optional[str], output_format: Optional[str]) -> Path:
    api_key = (os.getenv("SKILL_PILOT_API_KEY") or "").strip()
    base_url = (os.getenv("SKILL_PILOT_BASE_URL") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="SKILL_PILOT_API_KEY is not configured")
    if not base_url:
        raise HTTPException(status_code=500, detail="SKILL_PILOT_BASE_URL is not configured")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise HTTPException(status_code=500, detail="openai package is not installed") from exc

    model = provider.get("model", "skill-pilot-tts")
    selected_voice = voice or provider.get("voice", "alloy")
    instructions = provider.get("instructions", "Speak in a cheerful and positive tone.")
    fmt = (output_format or provider.get("format", "wav")).lower()
    if fmt not in {"mp3", "wav", "opus", "aac", "flac", "pcm"}:
        fmt = "wav"

    out = Path(f"/tmp/webui_tts_{uuid.uuid4().hex}.{fmt if fmt != 'pcm' else 'wav'}")
    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.audio.speech.create(
            model=model,
            voice=selected_voice,
            input=text,
            instructions=instructions,
            response_format=fmt,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Skill Pilot TTS error: {exc}") from exc

    raw = response.read()
    if not raw:
        raise HTTPException(status_code=502, detail="Skill Pilot TTS returned empty audio data")

    if fmt == "pcm":
        _write_wav(out, raw)
    else:
        out.write_bytes(raw)
    return out


def _openai_tts(text: str, provider: Dict[str, Any], voice: Optional[str], output_format: Optional[str]) -> Path:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise HTTPException(status_code=500, detail="openai package is not installed") from exc

    model = provider.get("model", "gpt-4o-mini-tts")
    selected_voice = voice or provider.get("voice", "alloy")
    instructions = provider.get("instructions", "Speak in a cheerful and positive tone.")
    fmt = (output_format or provider.get("format", "wav")).lower()
    if fmt not in {"mp3", "wav", "opus", "aac", "flac", "pcm"}:
        fmt = "wav"

    out = Path(f"/tmp/webui_tts_{uuid.uuid4().hex}.{fmt if fmt != 'pcm' else 'wav'}")
    client = OpenAI(api_key=api_key)

    try:
        response = client.audio.speech.create(
            model=model,
            voice=selected_voice,
            input=text,
            instructions=instructions,
            response_format=fmt,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI TTS error: {exc}") from exc

    raw = response.read()
    if not raw:
        raise HTTPException(status_code=502, detail="OpenAI TTS returned empty audio data")

    if fmt == "pcm":
        _write_wav(out, raw)
    else:
        out.write_bytes(raw)
    return out


def _gemini_tts(text: str, provider: Dict[str, Any], voice: Optional[str], output_format: Optional[str]) -> Path:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLEAI_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY or GOOGLEAI_API_KEY is not configured")

    model = provider.get("model", "gemini-2.5-flash-preview-tts")
    selected_voice = voice or provider.get("voice", "Kore")
    fmt = (output_format or provider.get("format", "wav")).lower()
    out = Path(f"/tmp/webui_tts_{uuid.uuid4().hex}.wav")

    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": selected_voice,
                    }
                }
            },
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    data = _http_post_json(url, payload, headers={})

    b64_audio = None
    candidates = data.get("candidates") or []
    for candidate in candidates:
        parts = ((candidate.get("content") or {}).get("parts") or [])
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data") or {}
            if inline.get("data"):
                b64_audio = inline.get("data")
                break
        if b64_audio:
            break

    if not b64_audio:
        raise HTTPException(status_code=502, detail="Gemini TTS returned no audio data")

    pcm_bytes = base64.b64decode(b64_audio)
    _write_wav(out, pcm_bytes)

    if fmt == "wav":
        return out

    converted = out.with_suffix(f".{fmt}")
    converted.write_bytes(out.read_bytes())
    return converted


def _media_mcp_tts(text: str, provider: Dict[str, Any], voice: Optional[str], output_format: Optional[str]) -> Path:
    _ = output_format
    voices = provider.get("voices")
    if not isinstance(voices, dict) or not voices:
        raise HTTPException(status_code=500, detail="Media MCP TTS provider is missing configured voices")

    selected_voice = voice or provider.get("voice")
    if selected_voice:
        selected_config = voices.get(selected_voice)
        if not isinstance(selected_config, dict):
            selected_voice = None
            selected_config = None
    else:
        selected_config = None

    if selected_voice is None or not isinstance(selected_config, dict):
        selected_voice, selected_config = next(iter(voices.items()))
        if not isinstance(selected_config, dict):
            raise HTTPException(status_code=500, detail=f"Invalid Media MCP TTS voice config: {selected_voice}")

    emotion = str(selected_config.get("emotion") or "").strip()
    emotion_sample = str(selected_config.get("emotion_sample") or "").strip()
    ref_voice = _normalize_media_mcp_input_reference(selected_config.get("ref_voice") or "")
    ref_emotion_voice = _normalize_media_mcp_input_reference(selected_config.get("ref_emotion_voice") or "")

    if not emotion:
        raise HTTPException(status_code=500, detail=f"Media MCP TTS voice '{selected_voice}' is missing emotion")
    if not emotion_sample:
        raise HTTPException(status_code=500, detail=f"Media MCP TTS voice '{selected_voice}' is missing emotion_sample")
    if not ref_voice:
        raise HTTPException(status_code=500, detail=f"Media MCP TTS voice '{selected_voice}' is missing ref_voice")

    repo_root = Path(__file__).resolve().parents[2]
    request = {
        "server_id": "media",
        "tool_name": "text_to_speech",
        "arguments": {
            "text": text,
            "emotion": emotion,
            "emotion_sample": emotion_sample,
            "ref_voice": ref_voice,
            "ref_emotion_voice": ref_emotion_voice or ref_voice,
        },
    }

    try:
        result = subprocess.run(
            [str(repo_root / "core/bin/tool-cli"), "request", json.dumps(request)],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Media MCP TTS failed: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise HTTPException(status_code=502, detail=f"Media MCP TTS failed: {stderr}")

    output = (result.stdout or "").strip()
    if not output:
        raise HTTPException(status_code=502, detail="Media MCP TTS returned no output")

    try:
        response = json.loads(output)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Media MCP TTS returned invalid JSON: {output}") from exc

    if not isinstance(response, dict):
        raise HTTPException(status_code=502, detail="Media MCP TTS returned an unexpected response")
    if response.get("status") != "ok":
        raise HTTPException(status_code=502, detail=str(response.get("detail") or "Media MCP TTS failed"))

    result_payload = response.get("result")
    raw_path = _extract_mcp_text_content(result_payload)
    if not raw_path and isinstance(result_payload, str):
        raw_path = result_payload.strip()
    if not raw_path:
        raise HTTPException(status_code=502, detail=f"Media MCP TTS returned no local audio path: {output}")

    path = Path(raw_path).expanduser()
    if not path.is_file():
        raise HTTPException(status_code=502, detail=f"Media MCP TTS returned a missing file path: {raw_path}")
    return path.resolve()


def text_to_speech_file(text: str, provider_id: Optional[str] = None, voice: Optional[str] = None, output_format: Optional[str] = None) -> str:
    provider = get_tts_provider(provider_id)
    provider_name = provider.get("id")

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    if provider_name == "skill-pilot":
        path = _skill_pilot_tts(text, provider, voice, output_format)
    elif provider_name == "openai":
        path = _openai_tts(text, provider, voice, output_format)
    elif provider_name == "gemini":
        path = _gemini_tts(text, provider, voice, output_format)
    elif provider_name == "media-mcp":
        path = _media_mcp_tts(text, provider, voice, output_format)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported TTS provider: {provider_name}")

    logger.info("Created TTS audio file: %s", path)
    return str(path)


async def async_text_to_audio_file(
    text: str,
    voice: str = "alloy",
    format: str = "wav",
    provider_id: Optional[str] = None,
    **_: Any,
) -> str:
    path = await asyncio.to_thread(
        text_to_speech_file,
        text,
        provider_id,
        voice,
        format,
    )
    return path
