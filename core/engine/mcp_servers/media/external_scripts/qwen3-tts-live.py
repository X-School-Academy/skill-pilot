#!/usr/bin/env python3
"""
Standalone websocket server for FasterQwen3TTS voice-clone streaming.

This server intentionally implements the small subset of the OpenAI realtime
websocket protocol consumed by `core/engine/mcp_servers/live_tts/main.py`:

- emits `session.created` when a client connects
- accepts `session.update` and replies with `session.updated`
- accepts `response.create`
- streams `response.audio.delta`, then `response.audio.done`, then `response.done`

Drop this file into `faster-qwen3-tts/qwen3-tts-live.py` on the remote server.
Reference voices are resolved from `faster-qwen3-tts/voices/{voice}.wav` and
fall back to `.mp3` when `.wav` is not present.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import signal
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import websockets
from faster_qwen3_tts import FasterQwen3TTS


SCRIPT_DIR = Path(__file__).resolve().parent
VOICES_DIR = SCRIPT_DIR / "voices"
DEFAULT_HOST = os.getenv("QWEN3_TTS_WS_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("QWEN3_TTS_WS_PORT", "8081"))
DEFAULT_MODEL = os.getenv("QWEN3_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
DEFAULT_LANGUAGE = os.getenv("QWEN3_TTS_LANGUAGE", "English")
DEFAULT_VOICE = os.getenv("QWEN3_TTS_DEFAULT_VOICE", "default")
DEFAULT_REF_TEXT = os.getenv("QWEN3_TTS_REF_TEXT", "").strip()
DEFAULT_CHUNK_SIZE = int(os.getenv("QWEN3_TTS_CHUNK_SIZE", "8"))
OUTPUT_SAMPLE_RATE = int(os.getenv("QWEN3_TTS_OUTPUT_SAMPLE_RATE", "24000"))

WHISPER_MODEL = os.getenv("QWEN3_TTS_WHISPER_MODEL", "openai/whisper-large-v3-turbo")

_MODEL: FasterQwen3TTS | None = None
_WHISPER: Any = None


def _get_whisper() -> Any:
    global _WHISPER
    if _WHISPER is None:
        import torch
        from transformers import pipeline

        logging.info("Loading Whisper model: %s", WHISPER_MODEL)
        _WHISPER = pipeline(
            "automatic-speech-recognition",
            model=WHISPER_MODEL,
            dtype=torch.float16,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
    return _WHISPER


def _transcribe_voice(voice_path: Path) -> str:
    logging.info("Transcribing '%s' with Whisper ...", voice_path.name)
    result = _get_whisper()(str(voice_path))
    text = result["text"].strip()
    text_path = voice_path.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")
    logging.info("Saved transcription to '%s'", text_path.name)
    return text


def _get_model() -> FasterQwen3TTS:
    global _MODEL
    if _MODEL is None:
        logging.info("Loading FasterQwen3TTS model: %s", DEFAULT_MODEL)
        _MODEL = FasterQwen3TTS.from_pretrained(DEFAULT_MODEL)
    return _MODEL


def _safe_voice_name(voice: str | None) -> str:
    candidate = (voice or DEFAULT_VOICE).strip()
    candidate = Path(candidate).name
    return candidate or DEFAULT_VOICE


def _resolve_voice_file(voice: str | None) -> Path:
    voice_name = _safe_voice_name(voice)
    for suffix in (".wav", ".mp3"):
        voice_path = VOICES_DIR / f"{voice_name}{suffix}"
        if voice_path.is_file():
            return voice_path
    raise FileNotFoundError(
        f"Voice '{voice_name}' not found. Expected {VOICES_DIR / (voice_name + '.wav')} "
        f"or {VOICES_DIR / (voice_name + '.mp3')}"
    )


def _resolve_ref_text(voice_path: Path) -> str:
    text_path = voice_path.with_suffix(".txt")
    if text_path.is_file():
        return text_path.read_text(encoding="utf-8").strip()
    if DEFAULT_REF_TEXT:
        return DEFAULT_REF_TEXT
    return _transcribe_voice(voice_path)


def _extract_text(event: dict[str, Any]) -> str:
    if isinstance(event.get("text"), str) and event["text"].strip():
        return event["text"].strip()

    response = event.get("response")
    if isinstance(response, dict):
        if isinstance(response.get("text"), str) and response["text"].strip():
            return response["text"].strip()

        parts: list[str] = []
        for item in response.get("input", []) or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n".join(parts)

    raise ValueError("No text content found in websocket request.")


def _to_pcm16(audio_chunk: Any, sample_rate: int) -> bytes:
    audio = np.asarray(audio_chunk)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=-1)

    if np.issubdtype(audio.dtype, np.floating):
        audio = np.clip(audio, -1.0, 1.0)
        audio = (audio * 32767.0).astype(np.int16)
    elif audio.dtype != np.int16:
        audio = np.clip(audio, -32768, 32767).astype(np.int16)

    if sample_rate != OUTPUT_SAMPLE_RATE and audio.size > 1:
        old_positions = np.linspace(0.0, 1.0, num=audio.size, endpoint=False)
        new_size = max(1, round(audio.size * OUTPUT_SAMPLE_RATE / sample_rate))
        new_positions = np.linspace(0.0, 1.0, num=new_size, endpoint=False)
        audio = np.interp(new_positions, old_positions, audio.astype(np.float32)).astype(np.int16)

    return audio.tobytes()


async def _send_event(websocket: Any, payload: dict[str, Any]) -> None:
    await websocket.send(json.dumps(payload))


async def _stream_tts_response(websocket: Any, text: str, voice: str) -> None:
    response_id = f"resp_{uuid.uuid4().hex}"
    voice_path = _resolve_voice_file(voice)
    ref_text = _resolve_ref_text(voice_path)
    model = _get_model()

    logging.info("Streaming TTS for voice=%s text_len=%s", voice_path.stem, len(text))

    for audio_chunk, sample_rate, _timing in model.generate_voice_clone_streaming(
        text=text,
        language=DEFAULT_LANGUAGE,
        ref_audio=str(voice_path),
        ref_text=ref_text,
        chunk_size=DEFAULT_CHUNK_SIZE,
    ):
        pcm_bytes = _to_pcm16(audio_chunk, sample_rate)
        if not pcm_bytes:
            continue
        await _send_event(
            websocket,
            {
                "type": "response.audio.delta",
                "response_id": response_id,
                "delta": base64.b64encode(pcm_bytes).decode("ascii"),
            },
        )

    await _send_event(websocket, {"type": "response.audio.done", "response_id": response_id})
    await _send_event(websocket, {"type": "response.done", "response": {"id": response_id}})


async def _handle_connection(websocket: Any) -> None:
    session_id = f"sess_{uuid.uuid4().hex}"
    voice = DEFAULT_VOICE

    await _send_event(
        websocket,
        {
            "type": "session.created",
            "session": {"id": session_id},
        },
    )

    async for raw_message in websocket:
        try:
            event = json.loads(raw_message)
            event_type = event.get("type")

            if event_type == "session.update":
                session = event.get("session", {})
                if isinstance(session, dict):
                    voice = _safe_voice_name(session.get("voice"))
                await _send_event(
                    websocket,
                    {
                        "type": "session.updated",
                        "session": {"id": session_id, "voice": voice},
                    },
                )
                continue

            if event_type == "response.create":
                text = _extract_text(event)
                await _stream_tts_response(websocket, text=text, voice=voice)
                continue

            if event_type == "response.cancel":
                await _send_event(websocket, {"type": "response.done", "response": {"cancelled": True}})
                continue

            logging.debug("Ignoring unsupported event: %s", event_type)
        except Exception as exc:
            logging.exception("Websocket request failed")
            await _send_event(
                websocket,
                {
                    "type": "error",
                    "error": {
                        "message": str(exc),
                    },
                },
            )


async def _run_server() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_shutdown() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            signal.signal(sig, lambda *_args: _request_shutdown())

    model = _get_model()
    if not model._warmed_up:
        await loop.run_in_executor(None, model._warmup, 100)

    async with websockets.serve(_handle_connection, DEFAULT_HOST, DEFAULT_PORT):
        logging.info("Qwen3 TTS live websocket server listening on ws://%s:%s", DEFAULT_HOST, DEFAULT_PORT)
        await stop_event.wait()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run_server())


if __name__ == "__main__":
    main()
