"""
Script execution helpers for the MCP server.

Wraps the existing GPU worker scripts (audio + vision) and provides a
consistent interface for running them either through ComfyUI's shell
workflow or directly via subprocess, depending on configuration.
"""

import asyncio
import os
import json
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from .gpu_workflow_executor import WorkflowExecutor, WorkflowExecutionError


# Environment variables
GPU_WORKER_TTS_CREATOR = os.getenv('GPU_WORKER_TTS_CREATOR')
GPU_WORKER_SONG_CREATOR = os.getenv('GPU_WORKER_SONG_CREATOR')
GPU_WORKER_LLM_VISION_INFER = os.getenv('GPU_WORKER_LLM_VISION_INFER')
GPU_WORKER_MUSETALK_CLI = os.getenv('GPU_WORKER_MUSETALK_CLI')
GPU_WORKER_WHISPER_CLI = os.getenv('GPU_WORKER_WHISPER_CLI')
PDF_READER_SCRIPT = os.getenv('PDF_READER_SCRIPT')
COMFYUI_INSTALL_PATH = str(os.getenv('COMFYUI_INSTALL_PATH') or '').rstrip('/')
COMFYUI_OUTPUT_DIR = f"{COMFYUI_INSTALL_PATH}/output"
SHELL_SCRIPT_WORKFLOW_ID = 'shell_script'

class ScriptExecutionError(Exception):
    """Raised when helper script execution fails"""
    pass


class ScriptExecutor:
    """Execute helper scripts via ComfyUI workflow or direct subprocess"""

    def __init__(self) -> None:
        self.workflow_executor = WorkflowExecutor()

    @staticmethod
    def _is_explicit_local_path(path_value: str) -> bool:
        text = str(path_value or "").strip()
        return text.startswith("/") or text.startswith("./") or text.startswith("../") or text.startswith("~")

    def _validate_local_if_explicit(self, path_value: str, label: str) -> str:
        text = str(path_value or "").strip()
        if not text:
            raise ScriptExecutionError(f"{label} is required")
        if self._is_explicit_local_path(text):
            resolved = Path(text).expanduser().resolve()
            if not resolved.exists():
                raise ScriptExecutionError(f"{label} not found: {resolved}")
            return str(resolved)
        return text

    @staticmethod
    def _require_sentence(value: str, label: str) -> str:
        stripped = str(value or '').strip()
        if not stripped:
            raise ScriptExecutionError(f'{label} is required')

        # Treat as sentence if it contains at least two words
        if len(stripped.split()) < 2:
            raise ScriptExecutionError(f'{label} should be a sentence (multiple words), not a single word')

        return stripped

    def _parse_script_output(
        self,
        text_output: str,
        output_tag: str,
        description: str
    ) -> Dict[str, Any]:
        start_tag = f'<{output_tag}>'
        end_tag = f'</{output_tag}>'

        end_index = text_output.rfind(end_tag)
        if end_index == -1:
            raise ScriptExecutionError(
                f"{description} script output missing </{output_tag}> block. Output: {text_output[:500]}"
            )

        start_index = text_output.rfind(start_tag, 0, end_index)
        if start_index == -1:
            raise ScriptExecutionError(
                f"{description} script output missing <{output_tag}> block. Output: {text_output[:500]}"
            )

        json_block = text_output[start_index + len(start_tag):end_index].strip()
        try:
            script_output = json.loads(json_block)
            if isinstance(script_output, dict) and script_output.get('error'):
                raise ScriptExecutionError(
                    f"{description} script returned error: {script_output.get('error', 'Unknown error')}"
                )
            return script_output
        except json.JSONDecodeError as exc:
            raise ScriptExecutionError(
                f"Failed to parse {description} script output: {exc}. JSON block: {json_block[:500]}"
            ) from exc

    def _extract_text_from_comfyui_history(self, history: Dict[str, Any]) -> str:
        outputs = history.get('outputs') or {}

        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue

            text_entries = node_output.get('text')
            if not text_entries:
                continue

            if isinstance(text_entries, list):
                # Collect any usable text strings inside the list
                candidates = []
                for entry in text_entries:
                    if isinstance(entry, dict):
                        text_value = entry.get('text')
                        if text_value:
                            candidates.append(str(text_value))
                    elif isinstance(entry, str) and entry.strip():
                        candidates.append(entry)

                # Use only when there is exactly one meaningful text value;
                # ignore multi-text lists (often token dumps) to avoid noise.
                if len(candidates) == 1:
                    return candidates[0]
            elif isinstance(text_entries, dict):
                text_value = text_entries.get('text')
                if text_value:
                    return str(text_value)
            elif isinstance(text_entries, str) and text_entries.strip():
                return text_entries

        raise ScriptExecutionError('ComfyUI shell workflow returned no text output')

    async def _execute_shell_script_via_comfyui(
        self,
        script_path: str,
        json_payload: str,
        description: str
    ) -> str:
        try:
            workflow = await self.workflow_executor.load_workflow(SHELL_SCRIPT_WORKFLOW_ID)
            command_node = None
            script_node = None

            for node in workflow.values():
                if not isinstance(node, dict):
                    continue
                inputs = node.get('inputs') or {}
                class_type = node.get('class_type')

                if (
                    class_type == 'CommandExecJsonNode'
                    and isinstance(inputs.get('json_input'), str)
                    and inputs.get('json_input') == '{{json-str}}'
                ):
                    command_node = inputs

                if (
                    class_type == 'PrimitiveString'
                    and isinstance(inputs.get('value'), str)
                    and inputs.get('value') == '{{script}}'
                ):
                    script_node = inputs

            if not command_node or not script_node:
                raise ScriptExecutionError('Shell script workflow is missing required nodes.')

            command_node['json_input'] = json_payload
            script_node['value'] = script_path

            prompt_id, client_id = await self.workflow_executor.queue_workflow(workflow)
            _, history = await self.workflow_executor.poll_completion(prompt_id, client_id)

            return self._extract_text_from_comfyui_history(history)
        except WorkflowExecutionError as e:
            raise ScriptExecutionError(f"{description} failed: {e}") from e

    async def _run_structured_script(
        self,
        script_path: Optional[str],
        payload: Dict[str, Any],
        description: str,
        output_tag: str = 'json-output'
    ) -> Dict[str, Any]:
        if not script_path:
            raise ScriptExecutionError(f"{description} script path is not configured")

        json_payload = json.dumps(payload)

        stdout_text = await self._execute_shell_script_via_comfyui(
            script_path,
            json_payload,
            description
        )

        return self._parse_script_output(stdout_text, output_tag, description)

    async def run_structured_script(
        self,
        script_path: Optional[str],
        payload: Dict[str, Any],
        description: str,
        output_tag: str = 'json-output'
    ) -> Dict[str, Any]:
        """
        Public helper for running JSON-based helper scripts so tools can
        execute additional GPU worker utilities (e.g., MuseTalk CLI).
        """
        return await self._run_structured_script(
            script_path=script_path,
            payload=payload,
            description=description,
            output_tag=output_tag
        )

    async def generate_tts_audio(
        self,
        text: str,
        emotion: str,
        emotion_sample: str,
        gender: str = "female",
        age: int = 30,
        ref_voice: str = "",
        ref_emotion_voice: str = ""
    ) -> str:
        if not text or not str(text).strip():
            raise ScriptExecutionError('Text is required for TTS generation')

        if not emotion or not str(emotion).strip():
            raise ScriptExecutionError('Emotion is required for TTS generation')

        emotion_sample_value = self._require_sentence(emotion_sample, 'Emotion sample')

        ref_voice_value = str(ref_voice or '').strip()
        if not ref_voice_value:
            raise ScriptExecutionError('Reference voice is required for TTS generation')
        resolved_ref_voice = self._validate_local_if_explicit(ref_voice_value, "Reference voice")

        ref_emotion_voice_value = str(ref_emotion_voice or '').strip()
        if ref_emotion_voice_value:
            resolved_ref_emotion_voice = self._validate_local_if_explicit(
                ref_emotion_voice_value,
                "Emotion reference voice"
            )
        else:
            resolved_ref_emotion_voice = resolved_ref_voice

        payload = {
            'text': text,
            'emotion': emotion,
            'emotion_sample': emotion_sample_value,
            'gender': gender,
            'age': age,
            'ref_voice': str(resolved_ref_voice),
            'ref_emotion_voice': str(resolved_ref_emotion_voice),
            'output_dir': COMFYUI_OUTPUT_DIR
        }

        result = await self._run_structured_script(
            GPU_WORKER_TTS_CREATOR,
            payload,
            "TTS generation",
            output_tag='json-output'
        )

        audio_file = result.get('audio_file')
        if not audio_file:
            raise ScriptExecutionError('TTS script returned no audio file')

        return audio_file

    async def generate_tts_lines_audio(
        self,
        lines: list[Dict[str, Any]],
        ref_voice: str
    ) -> list[str]:
        if not lines:
            raise ScriptExecutionError('At least one line is required for TTS generation')

        ref_voice_value = str(ref_voice or '').strip()
        if not ref_voice_value:
            raise ScriptExecutionError('Reference voice is required for multi-line TTS generation')
        resolved_ref_voice = self._validate_local_if_explicit(ref_voice_value, "Reference voice")

        validated_lines = []
        for index, line in enumerate(lines, start=1):
            if not isinstance(line, dict):
                raise ScriptExecutionError(
                    f"Line {index} must be an object with text, emotion, emotion_sample, and ref_emotion_voice"
                )

            text = str(line.get('text') or '').strip()
            emotion = str(line.get('emotion') or '').strip()
            emotion_sample_value = self._require_sentence(
                line.get('emotion_sample'),
                f"Emotion sample for line {index}"
            )
            ref_emotion_voice_value = str(line.get('ref_emotion_voice') or '').strip()
            if ref_emotion_voice_value:
                resolved_ref_emotion_voice = self._validate_local_if_explicit(
                    ref_emotion_voice_value,
                    f"Emotion reference voice for line {index}"
                )
            else:
                resolved_ref_emotion_voice = resolved_ref_voice

            if not text:
                raise ScriptExecutionError(f"Line {index} is missing text")
            if not emotion:
                raise ScriptExecutionError(f"Line {index} is missing emotion")

            line_payload = {
                'text': text,
                'emotion': emotion,
                'emotion_sample': emotion_sample_value,
                'ref_emotion_voice': str(resolved_ref_emotion_voice)
            }

            validated_lines.append(line_payload)

        payload = {
            'segments': validated_lines,
            'ref_voice': str(resolved_ref_voice),
            'output_dir': COMFYUI_OUTPUT_DIR
        }

        result = await self._run_structured_script(
            GPU_WORKER_TTS_CREATOR,
            payload,
            "Multi-line TTS generation",
            output_tag='json-output'
        )

        audio_files = result.get('audio_files')
        if not audio_files:
            raise ScriptExecutionError('TTS script returned no audio files for multi-line input')

        return audio_files

    async def generate_song_audio(
        self,
        lyrics: str,
        emotion: str = "calm",
        emotion_sample: Optional[str] = None,
        ref_voice: Optional[str] = None
    ) -> str:
        if not lyrics:
            raise ScriptExecutionError('Lyrics are required for song generation')

        payload = {
            'lyrics': lyrics,
            'emotion': emotion,
            'emotion_sample': emotion_sample or emotion,
            'ref_voice': ref_voice,
            'output_dir': COMFYUI_OUTPUT_DIR
        }

        result = await self._run_structured_script(
            GPU_WORKER_SONG_CREATOR,
            payload,
            "Song generation",
            output_tag='json-output'
        )

        audio_file = result.get('audio_file')
        if not audio_file:
            raise ScriptExecutionError('Song generation script returned no audio file')

        return audio_file

    async def run_musetalk_lipsync(
        self,
        audio_file: str,
        video_file: str,
        label: Optional[str] = None
    ) -> str:
        payload: Dict[str, Any] = {
            'audio_file': audio_file,
            'video_file': video_file,
            'output_file': f"{COMFYUI_OUTPUT_DIR}/{uuid.uuid4().hex}.mp4"
        }
        if label:
            payload['label'] = label

        result = await self._run_structured_script(
            GPU_WORKER_MUSETALK_CLI,
            payload,
            "MuseTalk lip-sync",
            output_tag='output'
        )

        video_path = result.get('video_file')
        if not video_path:
            raise ScriptExecutionError('MuseTalk lip-sync script returned no video output')

        return str(video_path)

    async def analyze_image(
        self,
        prompt: str,
        image_file: str,
        max_tokens: int = 512
    ) -> str:
        image_file = self._validate_local_if_explicit(image_file, "Image file")

        payload = {
            'prompt': prompt,
            'image_file': image_file,
            'max_tokens': max_tokens
        }

        result = await self._run_structured_script(
            GPU_WORKER_LLM_VISION_INFER,
            payload,
            "Image analysis",
            output_tag='json-output'
        )

        output_text = result.get('output')
        if not output_text:
            raise ScriptExecutionError('Vision script returned no output')

        return output_text

    async def analyze_video(
        self,
        prompt: str,
        video_file: str,
        frame_step: int = 16,
        max_frames: int = -1,
        max_tokens: int = 2048
    ) -> str:
        video_file = self._validate_local_if_explicit(video_file, "Video file")

        payload = {
            'prompt': prompt,
            'video_file': video_file,
            'frame_step': frame_step,
            'max_frames': max_frames,
            'max_tokens': max_tokens
        }

        result = await self._run_structured_script(
            GPU_WORKER_LLM_VISION_INFER,
            payload,
            "Video analysis",
            output_tag='json-output'
        )

        output_text = result.get('output')
        if not output_text:
            raise ScriptExecutionError('Vision script returned no output')

        return output_text

    async def transcribe_audio(
        self,
        audio_file: str,
        language: str = "en",
        use_fp16: bool = True
    ) -> list:
        """
        Transcribe audio file with word-level timestamps for video scene transitions.

        Args:
            audio_file: Path to the audio file to transcribe
            language: Language code (e.g., "en", "es", "fr")
            use_fp16: Use FP16 precision for faster processing

        Returns:
            List of segments with timing information
        """
        audio_file = self._validate_local_if_explicit(audio_file, "Audio file")

        payload = {
            'audio_file': audio_file,
            'language': language,
            'f16': use_fp16
        }

        result = await self._run_structured_script(
            GPU_WORKER_WHISPER_CLI,
            payload,
            "Audio transcription",
            output_tag='json-output'
        )

        segments = result.get('segments')
        if segments is None:
            raise ScriptExecutionError('Whisper script returned no segments')

        return segments

    async def read_pdf_text(
        self,
        pdf_file: str,
        page_from: int,
        count: int
    ) -> Dict[str, Any]:
        """
        Extract text from a PDF using the helper script.

        Args:
            pdf_file: Path to the PDF file
            page_from: Starting page number (1-indexed)
            count: Number of pages to read
        """
        pdf_path = Path(self._validate_local_if_explicit(pdf_file, "PDF file")).expanduser()

        if page_from < 1:
            raise ScriptExecutionError("page_from must be >= 1")

        if count < 1:
            raise ScriptExecutionError("count must be >= 1")

        script_path = PDF_READER_SCRIPT
        if not script_path:
            raise ScriptExecutionError("PDF_READER_SCRIPT environment variable not set")

        resolved_script = Path(script_path).expanduser()

        payload = {
            "pdf_file": str(pdf_path),
            "page_from": page_from,
            "count": count
        }

        result = await self._run_structured_script(
            script_path=str(resolved_script),
            payload=payload,
            description="PDF text extraction",
            output_tag='json-output'
        )

        text = result.get('text')
        pages_read = result.get('pages_read')
        total_pages = result.get('total_pages')

        if text is None or pages_read is None or total_pages is None:
            raise ScriptExecutionError('PDF reader script returned incomplete data')

        return {
            "text": text,
            "pages_read": int(pages_read),
            "total_pages": int(total_pages)
        }
