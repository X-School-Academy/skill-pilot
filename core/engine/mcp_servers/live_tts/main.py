import asyncio
import base64
import json
import logging
import os
import queue
import signal
import threading
import tempfile
import time
import wave
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import uuid
from mcp.server.fastmcp import FastMCP

_MISSING_DEPS: list[str] = []

try:
    import pyaudio
except ModuleNotFoundError:
    pyaudio = None  # type: ignore[assignment]
    _MISSING_DEPS.append("pyaudio")
    logging.warning(
        "Optional dependency 'pyaudio' is missing. Enable live-tts with: ./skillpilot.sh enable live-tts"
    )

try:
    import numpy as np
except ModuleNotFoundError:
    np = None  # type: ignore[assignment]
    _MISSING_DEPS.append("numpy")

try:
    import websockets
    import websockets.exceptions
except ModuleNotFoundError:
    websockets = None  # type: ignore[assignment]
    _MISSING_DEPS.append("websockets")

class LiveAPIProvider(Enum):
    OPENAI = "openai"
    AZURE = "azure"
    GEMINI = "gemini"
    QWEN3_TTS = "qwen3-tts"


def _env_str(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_str_default(name: str, default: str) -> str:
    return _env_str(name) or default

class AudioManager:
    """Manages audio playback using PyAudio"""
    
    def __init__(self):
        # Playback state (managed by the playback thread).
        self.is_playing = False
        self.audio_started = False
        self.audio_queue = queue.Queue()
        self.current_session = None
        self._stop_event = threading.Event()
        self._playback_thread = None
        self.audio_stream = None
        self.silent_data = b'\x00' * 1024  # Silent audio data
        # Request queuing for async calls
        self.request_queue = queue.Queue()
        self._request_processor_thread = None
        self._request_processor_active = False
        self._capture_lock = threading.Lock()
        self._capture_buffer = bytearray()
        self._capture_path: Optional[Path] = None
        
        # NEW: Track when audio has been requested but not yet completed
        self.audio_requested = False
        self._log_audio_stats = _env_str_default("LIVE_TTS_LOG_AUDIO_STATS", "0") == "1"
        self._last_non_silent_ts: Optional[float] = None
        self._output_device_name = _env_str("LIVE_TTS_OUTPUT_DEVICE_NAME")
        self._output_device_index: Optional[int] = None
        try:
            raw_index = _env_str("LIVE_TTS_OUTPUT_DEVICE_INDEX")
            if raw_index is not None:
                self._output_device_index = int(raw_index)
        except Exception:
            self._output_device_index = None
        
    def start_playback_thread(self):
        """Start the audio playback thread"""
        if self._playback_thread is None or not self._playback_thread.is_alive():
            self._stop_event.clear()
            self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._playback_thread.start()
    
    def _ensure_audio_stream(self, p):
        """Ensure audio stream is open and ready"""
        if self.audio_stream is None or not self.audio_stream.is_active():
            try:
                chosen_device_index: Optional[int] = None
                chosen_device_name: Optional[str] = None

                if self._output_device_index is not None:
                    try:
                        info = p.get_device_info_by_index(self._output_device_index)
                        if int(info.get("maxOutputChannels", 0)) > 0:
                            chosen_device_index = self._output_device_index
                            chosen_device_name = info.get("name")
                    except Exception:
                        chosen_device_index = None

                if chosen_device_index is None and self._output_device_name:
                    want = self._output_device_name.lower()
                    try:
                        for idx in range(p.get_device_count()):
                            info = p.get_device_info_by_index(idx)
                            if int(info.get("maxOutputChannels", 0)) <= 0:
                                continue
                            name = str(info.get("name", ""))
                            if want in name.lower():
                                chosen_device_index = idx
                                chosen_device_name = name
                                break
                    except Exception:
                        chosen_device_index = None

                try:
                    default_device = p.get_default_output_device_info()
                    logging.info(
                        "Using default output device: %s (index=%s)",
                        default_device.get("name"),
                        default_device.get("index"),
                    )
                except Exception:
                    pass

                if chosen_device_index is not None:
                    logging.info(
                        "Using configured output device: %s (index=%s)",
                        chosen_device_name or "?",
                        chosen_device_index,
                    )
                self.audio_stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=24000,
                    output=True,
                    output_device_index=chosen_device_index,
                    frames_per_buffer=2400  # 0.1 seconds
                )
                return True
            except Exception as e:
                logging.error(f"Error opening audio stream: {e}")
                return False
        return True
    
    def _close_audio_stream(self):
        """Safely close the audio stream"""
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception as e:
                logging.error(f"Error closing audio stream: {e}")
            finally:
                self.audio_stream = None
    
    def start_request_processor(self, tts_manager):
        """Start the request processor thread for queued async requests"""
        if self._request_processor_thread is None or not self._request_processor_thread.is_alive():
            self._request_processor_active = True
            self._request_processor_thread = threading.Thread(
                target=self._request_processor_loop, 
                args=(tts_manager,), 
                daemon=True
            )
            self._request_processor_thread.start()
    
    def _request_processor_loop(self, tts_manager):
        """Process queued async requests when service becomes available"""
        while self._request_processor_active and not self._stop_event.is_set():
            try:
                # Wait for service to be free
                while self.is_busy() and not self._stop_event.is_set():
                    time.sleep(0.1)
                
                if self._stop_event.is_set():
                    break
                
                # Get next request from queue
                try:
                    request = self.request_queue.get(timeout=1.0)
                    if request is None:  # Stop signal
                        break
                    
                    # Process the request
                    request_type, content = request
                    asyncio.run(self._process_queued_request(tts_manager, request_type, content))
                    self.request_queue.task_done()
                    
                except queue.Empty:
                    continue
                    
            except Exception as e:
                logging.error(f"Error in request processor: {e}")
    
    async def _process_queued_request(self, tts_manager, request_type: str, content: str):
        """Process a queued async request"""
        try:
            if request_type == "text_to_audio":
                await tts_manager._send_text_for_tts(content)
            elif request_type == "prompt_to_audio":
                await tts_manager._send_text_for_conversation(content)
        except Exception as e:
            logging.error(f"Error processing queued request: {e}")
    
    def queue_async_request(self, request_type: str, content: str):
        """Queue an async request for processing when service is free"""
        self.request_queue.put((request_type, content))
    
    def mark_audio_requested(self):
        """Mark that a remote audio response has been requested (streaming may follow)."""
        self.audio_requested = True

    def start_capture(self) -> Path:
        """Start capturing incoming PCM audio so it can be persisted as a WAV file."""
        capture_dir = Path(tempfile.gettempdir()) / "live_tts_audio"
        capture_dir.mkdir(parents=True, exist_ok=True)
        capture_path = capture_dir / f"{uuid.uuid4()}.wav"
        with self._capture_lock:
            self._capture_buffer = bytearray()
            self._capture_path = capture_path
        return capture_path
    
    def mark_audio_complete(self):
        """Mark that the remote audio response is complete (no more audio expected)."""
        self.audio_requested = False

    def append_capture_audio(self, audio_data: bytes):
        """Append a received PCM chunk to the current capture buffer."""
        with self._capture_lock:
            if self._capture_path is None:
                return
            self._capture_buffer.extend(audio_data)

    def finalize_capture(self) -> Optional[str]:
        """Write the captured PCM stream to a WAV file and return its path."""
        with self._capture_lock:
            capture_path = self._capture_path
            capture_bytes = bytes(self._capture_buffer)
            self._capture_path = None
            self._capture_buffer = bytearray()

        if capture_path is None:
            return None

        if not capture_bytes:
            try:
                capture_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

        with wave.open(str(capture_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(capture_bytes)
        return str(capture_path)
    
    def is_busy(self) -> bool:
        """Check if audio is currently playing, queued, or requested"""
        return self.is_playing or not self.audio_queue.empty() or self.audio_requested
    
    def _playback_loop(self):
        """Main playback loop running in separate thread"""
        try:
            # Initialize PyAudio
            p = pyaudio.PyAudio()
            
            while not self._stop_event.is_set():
                try:
                    # Get audio data from queue with timeout
                    audio_data = self.audio_queue.get(timeout=0.1)
                    
                    if audio_data is None:  # Stop signal
                        self.audio_queue.task_done()
                        break

                    # Initialize audio stream if needed
                    if not self.audio_started:
                        self.audio_started = True
                        logging.info("Audio playback started")
                    
                    if not self._ensure_audio_stream(p):
                        self.audio_queue.task_done()
                        continue
                    
                    # Write audio data to stream
                    try:
                        if self._log_audio_stats:
                            samples = np.frombuffer(audio_data, dtype=np.int16)
                            peak = int(np.max(np.abs(samples))) if samples.size else 0
                            if peak > 0:
                                self._last_non_silent_ts = time.time()
                            logging.info(
                                "Audio chunk stats: bytes=%s frames=%s peak=%s last_non_silent_age_s=%s",
                                len(audio_data),
                                samples.size,
                                peak,
                                None
                                if self._last_non_silent_ts is None
                                else round(time.time() - self._last_non_silent_ts, 3),
                            )
                        logging.info(f"Playing audio: {len(audio_data)} bytes")
                        self.is_playing = True
                        self.audio_stream.write(audio_data, exception_on_underflow=False)
                    except Exception as e:
                        logging.error(f"Error writing audio data: {e}")
                    finally:
                        self.is_playing = False
                    
                    self.audio_queue.task_done()
                    
                except queue.Empty:                    
                    if self.audio_queue.empty():
                        if self.audio_started:
                            self.audio_started = False
                            self._close_audio_stream()
                    
                    continue
                    
                except Exception as e:
                    logging.error(f"Error in playback loop: {e}")
                    self.is_playing = False
                    self._close_audio_stream()
                    self.audio_started = False
            
            # Cleanup on exit
            self._close_audio_stream()
            self.audio_started = False
            self.is_playing = False
                    
            p.terminate()
            
        except Exception as e:
            logging.error(f"Failed to initialize audio: {e}")
    
    def add_audio(self, audio_data: bytes):
        """Add audio data to playback queue"""
        self.append_capture_audio(audio_data)
        self.audio_queue.put(audio_data)
    
    def has_queued_requests(self) -> bool:
        """Check if there are queued async requests"""
        return not self.request_queue.empty()
    
    def stop(self):
        """Stop audio playback and request processing"""
        self._stop_event.set()
        self._request_processor_active = False
        
        self.is_playing = False
        self.audio_started = False
        self._close_audio_stream()
        
        self.audio_queue.put(None)  # Signal to stop audio playback
        self.request_queue.put(None)  # Signal to stop request processor

    def cancel_pending_audio(self):
        """Best-effort cancel of current/pending audio playback state."""
        try:
            while True:
                self.audio_queue.get_nowait()
                self.audio_queue.task_done()
        except queue.Empty:
            pass
        self.is_playing = False
        self.audio_started = False
        self.mark_audio_complete()
        with self._capture_lock:
            self._capture_path = None
            self._capture_buffer = bytearray()

class LiveTTSSession:
    """Manages a live TTS session with AI providers"""
    
    def __init__(self, provider: LiveAPIProvider, audio_manager: AudioManager):
        self.provider = provider
        self.audio_manager = audio_manager
        self.websocket = None
        self.is_connected = False
        self.is_ready = False
        self._listen_task = None
        self._ready_event = None

    def _uses_openai_realtime_protocol(self) -> bool:
        return self.provider in {
            LiveAPIProvider.OPENAI,
            LiveAPIProvider.AZURE,
            LiveAPIProvider.QWEN3_TTS,
        }

    def _get_realtime_voice(self) -> str:
        if self.provider == LiveAPIProvider.QWEN3_TTS:
            return _env_str("QWEN3_TTS_VOICE") or _env_str_default("OPENAI_VOICE", "default")
        return _env_str_default("OPENAI_VOICE", "alloy")
        
    async def connect(self):
        """Connect to the live API provider"""
        # Create a new ready event for this connection attempt
        self._ready_event = asyncio.Event()

        # OpenAI Realtime API supports the following audio formats:
        # https://github.com/run-llama/openai_realtime_client/blob/main/openai_realtime_client/client/realtime_client.py
        # The Live API supports the following audio formats:
        # Input audio format: Raw 16 bit PCM audio at 24kHz little-endian
        # Output audio format: Raw 16 bit PCM audio at 24kHz little-endian

        # Gemini Live API supports the following audio formats:
        # The Live API supports the following audio formats:
        # Input audio format: Raw 16 bit PCM audio at 16kHz little-endian
        # Output audio format: Raw 16 bit PCM audio at 24kHz little-endian
        
        try:
            if self.provider == LiveAPIProvider.OPENAI:
                await self._connect_openai()
            elif self.provider == LiveAPIProvider.AZURE:
                await self._connect_azure()
            elif self.provider == LiveAPIProvider.GEMINI:
                await self._connect_gemini()
            elif self.provider == LiveAPIProvider.QWEN3_TTS:
                await self._connect_qwen3_tts()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
            self.is_connected = True
            logging.info(f"Connected to {self.provider.value}")
            
        except Exception as e:
            logging.error(f"Failed to connect to {self.provider.value}: {e}")
            self.is_connected = False
            if self.websocket:
                try:
                    await self.websocket.close()
                except:
                    pass
                self.websocket = None
            raise
    
    async def _connect_openai(self):
        """Connect to OpenAI Realtime API"""
        api_key = _env_str("OPENAI_API_KEY")
        model = _env_str_default("OPENAI_LIVE_CHAT_MODEL", "gpt-4o-realtime-preview")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        url = f"wss://api.openai.com/v1/realtime?model={model}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.websocket = await websockets.connect(url, additional_headers=headers)
        
        # Start listening for responses in background
        self._listen_task = asyncio.create_task(self._listen_openai())
        
        # Wait for session to be ready (session.created event will trigger setup)
        await asyncio.wait_for(self._ready_event.wait(), timeout=10.0)
    
    async def _connect_azure(self):
        """Connect to Azure OpenAI Realtime API"""
        api_key = _env_str("AZURE_OPENAI_API_KEY")
        endpoint = _env_str("AZURE_OPENAI_ENDPOINT")
        model = _env_str_default("AZURE_OPENAI_MODEL", "gpt-4o-realtime-preview")
        api_version = _env_str_default("AZURE_OPENAI_API_VERSION", "2024-12-17")
        
        if not all([api_key, endpoint]):
            raise ValueError("Azure OpenAI configuration incomplete")
        
        # https://github.com/Azure-Samples/aisearch-openai-rag-audio/blob/36ef213205ee440a771bce6a6c27fb51e07b307a/app/backend/rtmt.py
        
        url = f"{endpoint.rstrip('/')}/openai/realtime?api-version={api_version}&deployment={model}"
        url = url.replace("https://", "wss://")
        
        headers = {
            "api-key": api_key,
            "x-ms-client-request-id": str(uuid.uuid4()) # Unique request ID for debugging
        }
        
        self.websocket = await websockets.connect(url, additional_headers=headers)
        
        # Start listening for responses in background
        self._listen_task = asyncio.create_task(self._listen_openai())  # Same protocol as OpenAI
        
        # Wait for session to be ready
        await asyncio.wait_for(self._ready_event.wait(), timeout=10.0)
    
    async def _connect_gemini(self):
        """Connect to Gemini Live API"""
        api_key = _env_str("GEMINI_API_KEY")
        model = _env_str_default("GEMINI_LIVE_CHAT_MODEL", "gemini-2.0-flash-live-001")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={api_key}"
        
        self.websocket = await websockets.connect(url, additional_headers={"Content-Type": "application/json"})
        
        # Setup session
        language = _env_str_default("LANGUAGE", "English")
        setup_message = {
            "setup": {
                "model": f"models/{model}",
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "language_code": "en-US" if language == "English" else "cmn-CN",
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": _env_str_default("GEMINI_VOICE", "Puck")
                            }
                        }
                    }
                },
                "system_instruction":  {
                    "parts": [
                        {
                            "text": """\
You will have two roles:
1. TTS: You will read the text exactly as provided, in a specified emotional or voice style.
2. Conversational AI: You will respond to prompts in a conversational manner.
If the request is to ask to read text, you will only read the text in the specified style without any additional words or commentary, or please respond to the prompt in a conversational manner.
"""
                        }
                    ]
                } 
            }
        }
        await self.websocket.send(json.dumps(setup_message))

        # Start listening for responses in background
        self._listen_task = asyncio.create_task(self._listen_gemini())
        
        # Wait for setup complete with timeout
        await asyncio.wait_for(self._ready_event.wait(), timeout=10.0)

    async def _connect_qwen3_tts(self):
        """Connect to a local Qwen3 TTS websocket server using the OpenAI-style realtime event flow."""
        url = _env_str_default("QWEN3_TTS_API_URL", "ws://127.0.0.1:8081")
        self.websocket = await websockets.connect(url)

        # The standalone Qwen3 TTS websocket server mirrors the subset of the OpenAI
        # realtime protocol that this client already consumes.
        self._listen_task = asyncio.create_task(self._listen_openai())

        await asyncio.wait_for(self._ready_event.wait(), timeout=10.0)
    
    async def _listen_openai(self):
        """Listen for OpenAI responses"""
        try:
            async for message in self.websocket:
                event = json.loads(message)
                event_type = event.get("type")
                logging.info(f"OpenAI event: {event_type}")
                
                if event_type == "session.created":
                    logging.info("%s session created - sending session update", self.provider.value)
                    # Send session update after receiving session.created (like reference)
                    setup_message = {
                        "type": "session.update",
                        "session": {
                            "modalities": ["text", "audio"],
                            "voice": self._get_realtime_voice(),
                            "input_audio_format": "pcm16",
                            "output_audio_format": "pcm16",
                            "turn_detection": {
                                "type": "server_vad",
                                "threshold": 0.5,
                                "prefix_padding_ms": 500,
                                "silence_duration_ms": 200
                            }
                        }
                    }
                    await self.websocket.send(json.dumps(setup_message))
                
                elif event_type == "session.updated":
                    logging.info("%s session updated - ready to accept commands", self.provider.value)
                    self.is_ready = True
                    self._ready_event.set()
                
                elif event_type == "response.audio.delta":
                    delta = event.get("delta")
                    if delta:
                        audio_bytes = base64.b64decode(delta)
                        # Add audio to queue immediately for real-time playback
                        self.audio_manager.add_audio(audio_bytes)
                        logging.info(f"Audio delta added to queue: {len(audio_bytes)} bytes")
                        
                elif event_type == "response.audio.done":
                    logging.info("Audio response complete")
                    # No more audio is expected for this response; playback thread will drain the queue.
                    self.audio_manager.mark_audio_complete()

                elif event_type == "response.done":
                    # Some responses may complete without emitting audio.done (e.g., failures or text-only turns).
                    self.audio_manager.mark_audio_complete()
                
                elif event_type == "error":
                    error_info = event.get("error", {})
                    logging.error("%s error: %s", self.provider.value, error_info)
                    # Ensure any waiter unblocks and pending audio is dropped.
                    self.audio_manager.cancel_pending_audio()
                    self.audio_manager.mark_audio_complete()
                    
                else:
                    logging.debug(f"Unhandled OpenAI event: {event_type}")
                        
        except asyncio.CancelledError:
            logging.info("%s listen task cancelled", self.provider.value)
            raise
        except websockets.exceptions.ConnectionClosed as e:
            logging.warning("%s WebSocket connection closed: %s", self.provider.value, e)
            self.is_connected = False
        except Exception as e:
            logging.error("Error listening to %s: %s", self.provider.value, e)
            self.is_connected = False
    
    async def _listen_gemini(self):
        """Listen for Gemini responses"""
        try:
            async for message in self.websocket:
                event = json.loads(message)
                
                # Check for setup complete
                if "setupComplete" in event:
                    logging.info("Gemini setup complete - ready to accept commands")
                    self.is_ready = True
                    self._ready_event.set()
                    continue
                
                server_content = event.get("serverContent")
                if server_content:
                    model_turn = server_content.get("modelTurn")
                    if model_turn:
                        parts = model_turn.get("parts", [])
                        for part in parts:
                            inline_data = part.get("inlineData")
                            if inline_data:
                                audio_data = inline_data.get("data")
                                if audio_data:
                                    audio_bytes = base64.b64decode(audio_data)
                                    # Add audio to queue immediately for real-time playback
                                    self.audio_manager.add_audio(audio_bytes)
                                    logging.info(f"Gemini audio chunk added to queue: {len(audio_bytes)} bytes")
                    
                    if server_content.get("interrupted"):
                        logging.info("Gemini turn interrupted")
                        self.audio_manager.cancel_pending_audio()
                        self.audio_manager.mark_audio_complete()

                    if server_content.get("generationComplete"):
                        logging.info("Gemini generation complete")

                    turn_complete = server_content.get("turnComplete")
                    if turn_complete:
                        logging.info("Gemini turn complete")
                        self.audio_manager.mark_audio_complete()
                        
        except asyncio.CancelledError:
            logging.info("Gemini listen task cancelled")
            raise
        except websockets.exceptions.ConnectionClosed as e:
            logging.warning(f"Gemini WebSocket connection closed: {e}")
            self.is_connected = False
            self.audio_manager.cancel_pending_audio()
        except Exception as e:
            logging.error(f"Error listening to Gemini: {e}")
            self.is_connected = False
            self.audio_manager.cancel_pending_audio()
    
    async def send_text_for_tts(self, text: str):
        """Send text for simple TTS (just read the text)"""
        if not self.is_connected or not self.is_ready:
            raise RuntimeError("Session not ready")
        
        try:
            if self._uses_openai_realtime_protocol():
                self.is_playing = True
                if self.provider == LiveAPIProvider.QWEN3_TTS:
                    await self._send_text_realtime_tts(text, wrap_text=False)
                else:
                    await self._send_text_realtime_tts(text, wrap_text=True)
            elif self.provider == LiveAPIProvider.GEMINI:
                self.is_playing = True
                await self._send_text_gemini_tts(text)
        except (websockets.exceptions.ConnectionClosed, ConnectionError) as e:
            logging.warning(f"Connection lost during send_text_for_tts: {e}")
            self.is_connected = False
            self.is_playing = False
            raise RuntimeError("Connection lost")
        except Exception as e:
            logging.error(f"Error sending text for TTS: {e}")
            raise
    
    async def send_text_for_conversation(self, text: str):
        """Send text for conversational response (AI responds to prompt)"""
        if not self.is_connected or not self.is_ready:
            raise RuntimeError("Session not ready")
        
        try:
            if self._uses_openai_realtime_protocol():
                self.is_playing = True
                await self._send_text_realtime_conversation(text)
            elif self.provider == LiveAPIProvider.GEMINI:
                self.is_playing = True
                await self._send_text_gemini_conversation(text)
        except (websockets.exceptions.ConnectionClosed, ConnectionError) as e:
            logging.warning(f"Connection lost during send_text_for_conversation: {e}")
            self.is_connected = False
            self.is_playing = False
            raise RuntimeError("Connection lost")
        except Exception as e:
            logging.error(f"Error sending text for conversation: {e}")
            raise
    
    async def _send_text_realtime_tts(self, text: str, emotion: str = "neutral", wrap_text: bool = True):
        """Send text to an OpenAI-style realtime websocket server for simple TTS."""
        text_prompt = (
            f"Repeat exactly: '{text}' in a '{emotion}' style. No additional words or commentary."
            if wrap_text
            else text
        )
        message = {
            "type": "response.create",
            "response": {
                "temperature": 0.6,
                "max_output_tokens": 4096,
                "input": [{
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text_prompt,
                        }
                    ]
                }],
                "instructions": (
                    "Repeat the text exactly as provided, applying the specified emotional or voice style. "
                    "Do not add any introductory phrases, explanations, or commentary in the audio output. "
                    "Speak only the text given, in the required tone."
                )
            }
        }
        logging.info(f"Sending TTS request: {text}")
        await self.websocket.send(json.dumps(message))

    async def _send_text_realtime_conversation(self, prompt: str):
        """Send prompt to an OpenAI-style realtime websocket server."""
        message = {
            "type": "response.create",
            "response": {
                "temperature": 0.6,
                "max_output_tokens": 4096,
                "input": [{
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}]
                }]
            }
        }
        logging.info(f"Sending conversation request: {prompt}")
        await self.websocket.send(json.dumps(message))
    
    async def _send_text_gemini_tts(self, text: str, emotion: str = ""):
        """Send text to Gemini for simple TTS (just read the text)"""
        # For TTS, we instruct Gemini to just read the text
        emotion = 'As a teacher talking to a student face to face to teach a subject.' if emotion == "" else emotion
        tts_instruction = f"You are a TTS role now. Please read the following text exactly in a {emotion} style without any additional words or commentary: '{text}'"
        message = {
            "client_content": {
                "turns": [{
                    "role": "user",
                    "parts": [{"text": tts_instruction}]
                }],
                "turn_complete": True
            }
        }
        await self.websocket.send(json.dumps(message))
    
    async def _send_text_gemini_conversation(self, prompt: str):
        """Send prompt to Gemini for conversational response"""
        # For conversation, we let Gemini respond naturally to the prompt
        message = {
            "client_content": {
                "turns": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "turn_complete": True
            }
        }
        await self.websocket.send(json.dumps(message))
    
    async def close(self):
        """Close the session"""
        self.is_connected = False
        
        # Cancel the listening task first
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logging.warning(f"Error cancelling listen task: {e}")
        
        # Close the websocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logging.warning(f"Error closing websocket: {e}")
            finally:
                self.websocket = None
                self._listen_task = None

class LiveTTSManager:
    """Main manager for Live TTS operations"""
    
    def __init__(self):
        self.audio_manager = AudioManager()
        self.session: Optional[LiveTTSSession] = None
        provider_name = _env_str_default("TTS_PROVIDER", LiveAPIProvider.OPENAI.value)
        self.provider = LiveAPIProvider.OPENAI
        self.set_provider(provider_name)
        self.is_ready = False
        self.audio_manager.start_playback_thread()
        self.audio_manager.start_request_processor(self)
    
    def set_provider(self, provider_name: str):
        """Set the AI provider"""
        try:
            self.provider = LiveAPIProvider(provider_name.lower())
        except ValueError:
            raise ValueError(f"Unsupported provider: {provider_name}")
    
    async def _ensure_connection(self):
        """Ensure we have an active connection, create if needed"""
        if not self.session or not self.session.is_connected or not self.session.is_ready:
            if self.session:
                try:
                    await self.session.close()
                except Exception as e:
                    logging.warning(f"Error closing previous session: {e}")
            
            logging.info(f"Establishing connection to {self.provider.value}...")
            self.session = LiveTTSSession(self.provider, self.audio_manager)
            await self.session.connect()
            self.is_ready = True
            logging.info(f"TTS Manager ready with {self.provider.value}")
    
    async def _send_text_for_tts(self, text: str):
        """Internal method to send text for TTS"""
        try:
            await self._ensure_connection()
            await self.session.send_text_for_tts(text)
        except Exception as e:
            raise
    
    async def _send_text_for_conversation(self, prompt: str):
        """Internal method to send text for conversation"""
        try:
            await self._ensure_connection()
            await self.session.send_text_for_conversation(prompt)
        except Exception as e:
            raise
    
    async def text_to_audio(self, text: str) -> dict[str, str]:
        """Convert text to audio, play it completely, and persist the WAV file."""
        if self.audio_manager.is_busy():
            return {
                "audio_file": "",
                "status_message": "service is busy, try again later",
            }
        
        audio_file_path = ""
        try:
            # NEW: Mark audio as requested immediately
            self.audio_manager.mark_audio_requested()
            capture_path = self.audio_manager.start_capture()
            audio_file_path = str(capture_path)
            
            await self._send_text_for_tts(text)
            
            # Wait for audio to finish playing
            timeout = 30.0  # wait time
            start_time = time.time()
            while self.audio_manager.is_busy():
                if time.time() - start_time > timeout:
                    logging.warning(f"Audio playback timeout after {timeout}s, extending for another 30 seconds...")
                    timeout += 30.0  # Extend timeout for next check
                await asyncio.sleep(0.1)

            finalized_audio = self.audio_manager.finalize_capture() or ""
            return {
                "audio_file": finalized_audio,
                "status_message": "audio playback completed",
            }
        except asyncio.CancelledError:
            self.audio_manager.cancel_pending_audio()
            return {
                "audio_file": "",
                "status_message": "cancelled",
            }
        except Exception as e:
            finalized_audio = self.audio_manager.finalize_capture() or ""
            self.audio_manager.is_playing = False
            self.audio_manager.mark_audio_complete()  # NEW: Mark complete on error
            self.audio_manager.cancel_pending_audio()
            logging.error(f"Error in text_to_audio: {e}")
            return {
                "audio_file": finalized_audio,
                "status_message": f"error: {str(e)}",
            }
    
    async def async_text_to_audio(self, text: str) -> str:
        """Convert text to audio and return immediately"""
        if self.audio_manager.is_busy():
            # Queue the request for later processing
            self.audio_manager.queue_async_request("text_to_audio", text)
            return "audio generation queued (service busy)"
        
        try:
            # NEW: Mark audio as requested immediately
            self.audio_manager.mark_audio_requested()
            
            await self._send_text_for_tts(text)
            return "audio generation started"
        except asyncio.CancelledError:
            self.audio_manager.cancel_pending_audio()
            return "cancelled"
        except Exception as e:
            self.audio_manager.mark_audio_complete()  # NEW: Mark complete on error
            logging.error(f"Error in async_text_to_audio: {e}")
            return f"error: {str(e)}"
    
    async def prompt_to_audio(self, prompt: str) -> str:
        """Send prompt to AI and play response audio completely before returning"""
        if self.audio_manager.is_busy():
            return "service is busy, try again later"
        
        try:
            # NEW: Mark audio as requested immediately
            self.audio_manager.mark_audio_requested()
            
            await self._send_text_for_conversation(prompt)
            
            # Wait for audio to finish playing
            timeout = 30.0  # wait time
            start_time = time.time()
            while self.audio_manager.is_busy():
                if time.time() - start_time > timeout:
                    logging.warning(f"Audio playback timeout after {timeout}s, extending for another 30 seconds...")
                    timeout += 30.0  # Extend timeout for next check
                await asyncio.sleep(0.1)
            
            return "audio response completed"
        except asyncio.CancelledError:
            self.audio_manager.cancel_pending_audio()
            return "cancelled"
        except Exception as e:
            self.audio_manager.is_playing = False
            self.audio_manager.mark_audio_complete()  # NEW: Mark complete on error
            logging.error(f"Error in prompt_to_audio: {e}")
            return f"error: {str(e)}"
    
    async def async_prompt_to_audio(self, prompt: str) -> str:
        """Send prompt to AI and return immediately"""
        if self.audio_manager.is_busy():
            # Queue the request for later processing
            self.audio_manager.queue_async_request("prompt_to_audio", prompt)
            return "audio response queued (service busy)"
        
        try:
            # NEW: Mark audio as requested immediately
            self.audio_manager.mark_audio_requested()
            
            await self._send_text_for_conversation(prompt)
            return "audio response generation started"
        except asyncio.CancelledError:
            self.audio_manager.cancel_pending_audio()
            return "cancelled"
        except Exception as e:
            self.audio_manager.mark_audio_complete()  # NEW: Mark complete on error
            logging.error(f"Error in async_prompt_to_audio: {e}")
            return f"error: {str(e)}"
    
    async def close(self):
        """Close all sessions and cleanup"""
        self.is_ready = False
        if self.session:
            await self.session.close()
            self.session = None
        self.audio_manager.stop()


logging.basicConfig(level=logging.INFO)

mcp = FastMCP("Live TTS MCP Server")
tts_manager: LiveTTSManager | None = None


def _ensure_tts_manager() -> LiveTTSManager:
    global tts_manager
    if _MISSING_DEPS:
        missing = ", ".join(sorted(set(_MISSING_DEPS)))
        raise RuntimeError(
            f"Missing live_tts dependencies: {missing}. "
            "Run './skillpilot.sh enable live-tts' from repo root to install optional dependencies."
        )
    if tts_manager is None:
        tts_manager = LiveTTSManager()
    return tts_manager


def _close_tts_manager() -> None:
    global tts_manager
    if tts_manager is None:
        return
    try:
        asyncio.run(tts_manager.close())
    except Exception as exc:
        logging.warning("Error while closing LiveTTSManager: %s", exc)
    finally:
        tts_manager = None


@mcp.tool()
async def text_to_audio(text: str) -> dict[str, str]:
    """
    Convert text to audio, play it completely, and save it to a temporary WAV file.

    Args:
        text: The text to convert to speech.

    Returns:
        JSON object containing the saved audio path and a status message.
    """
    manager = _ensure_tts_manager()
    try:
        return await manager.text_to_audio(text)
    except asyncio.CancelledError:
        try:
            manager.audio_manager.cancel_pending_audio()
        except Exception:
            pass
        return {
            "audio_file": "",
            "status_message": "cancelled",
        }


def _cleanup_and_exit(*_args) -> None:
    _close_tts_manager()
    raise SystemExit(0)


def main() -> None:
    if _MISSING_DEPS:
        missing = ", ".join(sorted(set(_MISSING_DEPS)))
        logging.warning(
            "Live TTS optional dependencies are missing: %s. Run './skillpilot.sh enable live-tts' from repo root.",
            missing,
        )

    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)

    try:
        mcp.run(transport="stdio")
    finally:
        _close_tts_manager()


if __name__ == "__main__":
    main()
