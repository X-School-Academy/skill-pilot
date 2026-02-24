import base64
import asyncio
import json
import os
import uuid
import wave
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from llm_service import get_tts_provider
from settings import DEFAULT_TTS_PROVIDER, logger


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


def _openai_tts(text: str, provider: Dict[str, Any], voice: Optional[str], output_format: Optional[str]) -> Path:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise HTTPException(status_code=500, detail="openai package is not installed") from exc

    model = provider.get("model", "gpt-audio")
    selected_voice = voice or provider.get("voice", "alloy")
    fmt = (output_format or provider.get("format", "wav")).lower()
    if fmt not in {"mp3", "wav", "opus", "aac", "flac", "pcm"}:
        fmt = "wav"

    out = Path(f"/tmp/webui_tts_{uuid.uuid4().hex}.{fmt if fmt != 'pcm' else 'wav'}")
    client = OpenAI(api_key=api_key)

    try:
        completion = client.chat.completions.create(
            model=model,
            modalities=["text", "audio"],
            audio={"voice": selected_voice, "format": fmt},
            messages=[{"role": "user", "content": text}],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI TTS error: {exc}") from exc

    try:
        audio_data = completion.choices[0].message.audio.data
    except Exception as exc:
        raise HTTPException(status_code=502, detail="OpenAI TTS returned no audio data") from exc

    if not audio_data:
        raise HTTPException(status_code=502, detail="OpenAI TTS returned empty audio data")

    raw = base64.b64decode(audio_data)
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


def text_to_speech_file(text: str, provider_id: Optional[str] = None, voice: Optional[str] = None, output_format: Optional[str] = None) -> str:
    provider = get_tts_provider(provider_id or DEFAULT_TTS_PROVIDER)
    provider_name = provider.get("id")

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    if provider_name == "openai":
        path = _openai_tts(text, provider, voice, output_format)
    elif provider_name == "gemini":
        path = _gemini_tts(text, provider, voice, output_format)
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
) -> tuple[str, float]:
    path = await asyncio.to_thread(
        text_to_speech_file,
        text,
        provider_id,
        voice,
        format,
    )
    return path, 0.0
