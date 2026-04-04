"""
ComfyUI Workflow Executor for MCP Server

Extracted from gpu_task_worker.py for standalone workflow execution
without Strapi task queue dependencies.
"""

import os
import json
import uuid
import hashlib
import aiohttp
import asyncio
import aiofiles
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from urllib.parse import quote


# Configuration
COMFYUI_SERVER_ADDRESS = os.getenv('COMFYUI_SERVER_ADDRESS', 'http://localhost:8188')
COMFYUI_UPLOAD_SUBFOLDER = os.getenv('COMFYUI_UPLOAD_SUBFOLDER', '').strip()
GPU_WORKER_MAX_EXECUTION_TIME = int(os.getenv('GPU_WORKER_MAX_EXECUTION_TIME', '600'))
GPU_WORKER_RETRY_ATTEMPTS = int(os.getenv('GPU_WORKER_RETRY_ATTEMPTS', '3'))
GPU_WORKER_COMFYUI_CONNECTION_FAILURE_LIMIT = int(
    os.getenv('GPU_WORKER_COMFYUI_CONNECTION_FAILURE_LIMIT', '5')
)
GPU_WORKER_COMFYUI_SERVER_DOWN_GRACE_SECONDS = int(
    os.getenv('GPU_WORKER_COMFYUI_SERVER_DOWN_GRACE_SECONDS', '30')
)
GPU_WORKER_COMFYUI_QUEUE_IDLE_FAIL_SECONDS = int(
    os.getenv('GPU_WORKER_COMFYUI_QUEUE_IDLE_FAIL_SECONDS', '20')
)

# Workflow directory
WORKFLOW_DIR = Path(__file__).parent / 'gpu_workflow'

# Output keywords for file classification
AUDIO_OUTPUT_KEYWORDS = {
    'jit_api_image': 'image_url',
    'jit_api_thumbnail': 'thumbnail_url',
    'jit_api_raw_video': 'raw_video_url',
    'jit_api_upscaled_video': 'upscaled_video_url',
    'jit_api_raw_split_1_video': 'raw_split_1_video_url',
    'jit_api_raw_split_2_video': 'raw_split_2_video_url',
    'jit_api_upscaled_split_1_video': 'upscaled_split_1_video_url',
    'jit_api_upscaled_split_2_video': 'upscaled_split_2_video_url'
}

# Keep placeholder aliases aligned with gpu_task_worker so workflows that rely on
# legacy names like {{ref_audio}} continue to work even if tools only pass
# {{audio_file}} paths.
AUDIO_PLACEHOLDER_ALIASES = {
    '{{audio_file}}': ['{{ref_audio}}'],
    '{{audio_file1}}': ['{{audio_file_1}}', '{{ref_audio_1}}'],
    '{{audio_file2}}': ['{{audio_file_2}}', '{{ref_audio_2}}']
}


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails"""
    pass


class OutOfMemoryError(WorkflowExecutionError):
    """Raised when ComfyUI runs out of memory"""
    pass


def _resolve_max_execution_time_seconds() -> int:
    """
    Resolve the workflow timeout in seconds.

    Prefer the explicit GPU worker timeout. If it is not set, fall back to the MCP
    tool timeout, which is stored in milliseconds in config/mcp.json5.
    """
    raw_gpu_timeout = str(os.getenv('GPU_WORKER_MAX_EXECUTION_TIME') or '').strip()
    if raw_gpu_timeout:
        try:
            timeout_seconds = int(raw_gpu_timeout)
        except ValueError as exc:
            raise WorkflowExecutionError(
                f"Invalid GPU_WORKER_MAX_EXECUTION_TIME value: {raw_gpu_timeout!r}"
            ) from exc
        if timeout_seconds > 0:
            return timeout_seconds

    raw_mcp_timeout = str(os.getenv('MCP_TOOL_TIMEOUT') or '').strip()
    if raw_mcp_timeout:
        try:
            timeout_ms = int(raw_mcp_timeout)
        except ValueError as exc:
            raise WorkflowExecutionError(
                f"Invalid MCP_TOOL_TIMEOUT value: {raw_mcp_timeout!r}"
            ) from exc
        if timeout_ms > 0:
            return max(1, int(timeout_ms / 1000))

    return GPU_WORKER_MAX_EXECUTION_TIME


def _build_local_upload_cache_key(local_path: str, upload_type: str = "input") -> str:
    path = Path(local_path).expanduser().resolve()
    stat = path.stat()
    return ":".join(
        [
            upload_type,
            str(path),
            str(stat.st_size),
            str(stat.st_mtime_ns),
        ]
    )


def _build_cached_remote_filename(local_path: str) -> str:
    file_path = Path(local_path).expanduser().resolve()
    stat = file_path.stat()
    suffix = file_path.suffix or '.bin'
    stem = ''.join(ch if ch.isalnum() or ch in {'_', '-'} else '_' for ch in file_path.stem).strip('_')
    stem = stem or 'input'
    fingerprint = hashlib.sha1(
        f"{file_path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode('utf-8')
    ).hexdigest()[:12]
    return f"{stem}_{fingerprint}{suffix}"


class WorkflowExecutor:
    """Execute ComfyUI workflows without Strapi task queue"""

    def __init__(self, tmp_dir: str = "/tmp/mcp_comfyui"):
        """
        Initialize WorkflowExecutor

        Args:
            tmp_dir: Directory for temporary files
        """
        self.tmp_dir = Path(tmp_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self._uploaded_to_comfy_by_local_file: Dict[str, Dict[str, str]] = {}

    async def load_workflow(self, workflow_id: str) -> Dict:
        """
        Load workflow JSON from file.

        Args:
            workflow_id: Workflow identifier (e.g., 'image-to-video')

        Returns:
            Workflow JSON as dictionary
        """
        workflow_file = WORKFLOW_DIR / f'workflow_{workflow_id}.json'

        if not workflow_file.exists():
            raise WorkflowExecutionError(f"Workflow file not found: {workflow_file}")

        try:
            async with aiofiles.open(workflow_file, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            raise WorkflowExecutionError(f"Failed to load workflow {workflow_id}: {str(e)}")

    async def replace_placeholders(
        self,
        workflow: Dict,
        task_input: Dict,
        downloaded_files: Dict[str, str]
    ) -> Dict:
        """Replace placeholders in workflow JSON with values suitable for remote ComfyUI execution."""
        replacements: dict[str, Any] = {}

        for key, value in task_input.items():
            replacements[f'{{{{{key}}}}}'] = value

        uploaded_files = await self._upload_placeholder_files(downloaded_files)
        for placeholder, refs in uploaded_files.items():
            replacements[placeholder] = refs

        def _apply(value: Any, parent_key: Optional[str] = None) -> Any:
            if isinstance(value, dict):
                return {k: _apply(v, k) for k, v in value.items()}
            if isinstance(value, list):
                return [_apply(item, parent_key) for item in value]
            if isinstance(value, str):
                updated = value
                for placeholder, replacement in replacements.items():
                    if placeholder not in updated:
                        continue

                    replacement_value = replacement
                    if isinstance(replacement, dict):
                        if parent_key == 'image':
                            replacement_value = replacement.get('name') or replacement.get('path')
                        else:
                            replacement_value = replacement.get('path') or replacement.get('name')

                    if updated == placeholder and not isinstance(replacement_value, str):
                        return replacement_value
                    updated = updated.replace(placeholder, str(replacement_value))
                return updated
            return value

        return _apply(workflow)

    async def _upload_placeholder_files(
        self,
        downloaded_files: Dict[str, str]
    ) -> Dict[str, Dict[str, str]]:
        """Upload local input files to ComfyUI and build placeholder references."""
        normalized_files = dict(downloaded_files)
        for canonical, aliases in AUDIO_PLACEHOLDER_ALIASES.items():
            if canonical in normalized_files:
                for alias in aliases:
                    normalized_files.setdefault(alias, normalized_files[canonical])

        uploaded_by_local_path: Dict[str, Dict[str, str]] = {}
        uploaded_by_placeholder: Dict[str, Dict[str, str]] = {}
        timeout = aiohttp.ClientTimeout(total=120, connect=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for placeholder, local_path in normalized_files.items():
                local_path_str = str(local_path).strip()
                if not local_path_str:
                    raise WorkflowExecutionError(f'Placeholder {placeholder} has an empty input path')

                candidate_path = Path(local_path_str).expanduser()
                if candidate_path.exists() and candidate_path.is_file():
                    resolved_path = str(candidate_path.resolve())
                    if resolved_path in uploaded_by_local_path:
                        uploaded_by_placeholder[placeholder] = uploaded_by_local_path[resolved_path]
                        continue

                    cache_key = _build_local_upload_cache_key(resolved_path)
                    cached_refs = self._uploaded_to_comfy_by_local_file.get(cache_key)
                    if cached_refs:
                        uploaded_by_local_path[resolved_path] = cached_refs
                        uploaded_by_placeholder[placeholder] = cached_refs
                        continue

                    refs = await self._upload_single_file(session, resolved_path)
                    uploaded_by_local_path[resolved_path] = refs
                    self._uploaded_to_comfy_by_local_file[cache_key] = refs
                    uploaded_by_placeholder[placeholder] = refs
                else:
                    # Already a ComfyUI-side path reference (e.g., input/abc.png).
                    uploaded_by_placeholder[placeholder] = {
                        "name": Path(local_path_str).name,
                        "path": local_path_str,
                    }

        return uploaded_by_placeholder

    async def _upload_single_file(
        self,
        session: aiohttp.ClientSession,
        local_path: str
    ) -> Dict[str, str]:
        """Upload one local input file to ComfyUI and return references for workflow placeholders."""
        file_path = Path(local_path).expanduser().resolve()
        if not file_path.exists() or not file_path.is_file():
            raise WorkflowExecutionError(f"Input file not found for ComfyUI upload: {file_path}")

        upload_attempts = [
            ("/upload/image", "image"),
            ("/upload", "file"),
            ("/upload", "image"),
        ]
        upload_name = _build_cached_remote_filename(str(file_path))
        upload_payload: Optional[Dict[str, Any]] = None
        last_error = ""

        for endpoint, field_name in upload_attempts:
            data = aiohttp.FormData()
            data.add_field("overwrite", "false")
            data.add_field("type", "input")
            if COMFYUI_UPLOAD_SUBFOLDER:
                data.add_field("subfolder", COMFYUI_UPLOAD_SUBFOLDER)

            content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            with file_path.open("rb") as file_handle:
                data.add_field(
                    field_name,
                    file_handle,
                    filename=upload_name,
                    content_type=content_type,
                )
                try:
                    url = f"{COMFYUI_SERVER_ADDRESS}{endpoint}"
                    async with session.post(url, data=data) as response:
                        if response.status in {200, 201}:
                            try:
                                payload = await response.json()
                            except Exception:
                                payload = {}
                            upload_payload = payload if isinstance(payload, dict) else {}
                            break
                        last_error = f"{endpoint} returned HTTP {response.status}"
                except Exception as exc:
                    last_error = f"{endpoint} request failed: {exc}"

        if upload_payload is None:
            raise WorkflowExecutionError(
                f"Failed to upload input file to ComfyUI ({file_path.name}): {last_error}"
            )

        uploaded_name = (
            upload_payload.get("name")
            or upload_payload.get("filename")
            or upload_name
        )
        uploaded_subfolder = str(upload_payload.get("subfolder") or COMFYUI_UPLOAD_SUBFOLDER or "").strip("/")
        uploaded_type = str(upload_payload.get("type") or "input").strip("/")

        if upload_payload.get("path"):
            path_ref = str(upload_payload["path"])
        elif upload_payload.get("fullpath"):
            path_ref = str(upload_payload["fullpath"])
        elif uploaded_subfolder:
            path_ref = f"{uploaded_subfolder}/{uploaded_name}"
        elif uploaded_type:
            path_ref = f"{uploaded_type}/{uploaded_name}"
        else:
            path_ref = uploaded_name

        return {
            "name": uploaded_name,
            "path": path_ref,
        }

    async def queue_workflow(self, workflow: Dict) -> Tuple[str, str]:
        """
        Submit workflow to ComfyUI API.

        Args:
            workflow: Workflow JSON to execute

        Returns:
            Tuple of (prompt_id, client_id)
        """
        client_id = str(uuid.uuid4())

        payload = {
            'prompt': workflow,
            'client_id': client_id
        }

        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        for attempt in range(GPU_WORKER_RETRY_ATTEMPTS):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    url = f"{COMFYUI_SERVER_ADDRESS}/prompt"
                    async with session.post(url, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise WorkflowExecutionError(
                                f"ComfyUI API error: {response.status} - {error_text}"
                            )

                        data = await response.json()
                        prompt_id = data.get('prompt_id')

                        if not prompt_id:
                            raise WorkflowExecutionError("No prompt_id returned from ComfyUI")

                        return prompt_id, client_id
            except Exception as e:
                if attempt < GPU_WORKER_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise WorkflowExecutionError(
                        f"Failed to queue workflow after {GPU_WORKER_RETRY_ATTEMPTS} attempts: {str(e)}"
                    )

    async def _get_queue_remaining(self, session: aiohttp.ClientSession) -> Optional[int]:
        """Get number of remaining items in ComfyUI queue"""
        try:
            url = f"{COMFYUI_SERVER_ADDRESS}/prompt"
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                queue_response = await response.json()
                exec_info = queue_response.get('exec_info') or {}
                return exec_info.get('queue_remaining')
        except Exception:
            return None

    def _outputs_contain_unfinished_batch(self, outputs: Dict[str, Any]) -> bool:
        """Check if outputs indicate an unfinished batch"""
        for node_output in outputs.values():
            if isinstance(node_output, dict) and 'unfinished_batch' in node_output:
                return True
        return False

    def _get_history_client_id(self, history: Dict[str, Any]) -> Optional[str]:
        """
        Extract client_id from a ComfyUI history entry.

        Supports both legacy ('prompts') and current ('prompt') response shapes.
        """

        def _get_client_block(key: str) -> Optional[Dict[str, Any]]:
            prompt_entry = history.get(key)
            if isinstance(prompt_entry, list) and len(prompt_entry) >= 4:
                block = prompt_entry[3]
                if isinstance(block, dict):
                    return block
            return None

        client_block = _get_client_block('prompt') or _get_client_block('prompts')
        if not client_block:
            return None

        client_id = client_block.get('client_id')
        if isinstance(client_id, str) and client_id:
            return client_id
        return None

    def _select_history_entry_by_client_id(
        self,
        history_payload: Dict[str, Any],
        client_id: str
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Find the first completed history entry that matches client_id."""
        if not isinstance(history_payload, dict):
            return None

        for workflow_id, entry in history_payload.items():
            if not isinstance(entry, dict):
                continue

            outputs = entry.get('outputs') or {}
            if not outputs:
                continue

            entry_client_id = self._get_history_client_id(entry)
            if entry_client_id != client_id:
                continue

            if self._outputs_contain_unfinished_batch(outputs):
                continue

            return workflow_id, entry

        return None

    async def _poll_history_for_client_id(
        self,
        client_id: str,
        start_time: float,
        max_wait_time: int,
        timeout: aiohttp.ClientTimeout
    ) -> Tuple[str, Dict[str, Any]]:
        """Poll /history to resolve batches that report unfinished_batch outputs."""
        connection_failure_count = 0
        connection_failure_started_at: Optional[float] = None

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                raise WorkflowExecutionError(f"Workflow execution timeout after {max_wait_time}s")

            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    url = f"{COMFYUI_SERVER_ADDRESS}/history"
                    async with session.get(url) as response:
                        if response.status != 200:
                            if response.status >= 500:
                                connection_failure_count += 1
                                if connection_failure_started_at is None:
                                    connection_failure_started_at = asyncio.get_event_loop().time()
                                failure_window = asyncio.get_event_loop().time() - connection_failure_started_at
                                if (
                                    connection_failure_count >= GPU_WORKER_COMFYUI_CONNECTION_FAILURE_LIMIT
                                    or failure_window >= GPU_WORKER_COMFYUI_SERVER_DOWN_GRACE_SECONDS
                                ):
                                    raise WorkflowExecutionError(
                                        'ComfyUI server became unreachable while monitoring workflow batches. Please try again later.'
                                    )
                            await asyncio.sleep(2)
                            continue

                        history_payload = await response.json()
                        connection_failure_count = 0
                        connection_failure_started_at = None

                        match = self._select_history_entry_by_client_id(history_payload, client_id)
                        if match:
                            return match

            except (aiohttp.ClientConnectorError, aiohttp.ClientOSError,
                    aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as conn_error:
                connection_failure_count += 1
                if connection_failure_started_at is None:
                    connection_failure_started_at = asyncio.get_event_loop().time()
                failure_window = asyncio.get_event_loop().time() - connection_failure_started_at
                if (
                    connection_failure_count >= GPU_WORKER_COMFYUI_CONNECTION_FAILURE_LIMIT
                    or failure_window >= GPU_WORKER_COMFYUI_SERVER_DOWN_GRACE_SECONDS
                ):
                    raise WorkflowExecutionError(
                        'Unable to reach ComfyUI server while monitoring workflow batches. Please verify the server status.'
                    )
            except Exception:
                # Unexpected parsing/logic errors should not break polling; keep waiting.
                pass

            await asyncio.sleep(2)

    async def poll_completion(
        self,
        prompt_id: str,
        client_id: Optional[str] = None,
        max_wait_time: int = None
    ) -> Tuple[str, Dict]:
        """
        Poll ComfyUI history endpoint until workflow completes.

        Args:
            prompt_id: ComfyUI prompt ID to monitor
            client_id: Optional client ID (for batch monitoring)
            max_wait_time: Maximum time to wait in seconds

        Returns:
            Tuple of (prompt_id, history data with outputs)
        """
        if max_wait_time is None:
            max_wait_time = _resolve_max_execution_time_seconds()

        start_time = asyncio.get_event_loop().time()
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connection_failure_count = 0
        connection_failure_started_at: Optional[float] = None
        queue_idle_started_at: Optional[float] = None

        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                raise WorkflowExecutionError(f"Workflow execution timeout after {max_wait_time}s")

            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    url = f"{COMFYUI_SERVER_ADDRESS}/history/{prompt_id}"
                    async with session.get(url) as response:
                        if response.status != 200:
                            if response.status >= 500:
                                connection_failure_count += 1
                                if connection_failure_started_at is None:
                                    connection_failure_started_at = asyncio.get_event_loop().time()
                                failure_window = asyncio.get_event_loop().time() - connection_failure_started_at
                                if (
                                    connection_failure_count >= GPU_WORKER_COMFYUI_CONNECTION_FAILURE_LIMIT
                                    or failure_window >= GPU_WORKER_COMFYUI_SERVER_DOWN_GRACE_SECONDS
                                ):
                                    raise WorkflowExecutionError(
                                        'ComfyUI server became unreachable. Please try again later.'
                                    )
                            else:
                                connection_failure_count = 0
                                connection_failure_started_at = None
                            await asyncio.sleep(2)
                            continue

                        history_response = await response.json()
                        connection_failure_count = 0
                        connection_failure_started_at = None
                        history = history_response.get(prompt_id, {})
                        outputs = history.get('outputs') or {}

                        # Check if workflow completed
                        if outputs:
                            queue_idle_started_at = None
                            if not self._outputs_contain_unfinished_batch(outputs):
                                return prompt_id, history

                            target_client_id = client_id or self._get_history_client_id(history)
                            if target_client_id:
                                return await self._poll_history_for_client_id(
                                    target_client_id,
                                    start_time,
                                    max_wait_time,
                                    timeout
                                )

                        # Check for errors
                        if 'status' in history:
                            status = history['status']
                            if status.get('status_str') == 'error':
                                error_msg = status.get('messages', ['Unknown error'])

                                # Check if this is an OOM error
                                messages = status.get('messages', [])
                                for message in messages:
                                    if isinstance(message, list) and len(message) >= 2:
                                        if message[0] == 'execution_error' and isinstance(message[1], dict):
                                            exception_type = message[1].get('exception_type', '')
                                            if exception_type == 'torch.OutOfMemoryError':
                                                raise OutOfMemoryError(
                                                    f"ComfyUI OOM: {message[1].get('exception_message', 'Out of memory')}"
                                                )

                                # Not an OOM error, raise regular workflow error
                                raise WorkflowExecutionError(f"ComfyUI workflow error: {error_msg}")

                        # Check queue status
                        queue_remaining = await self._get_queue_remaining(session)
                        if queue_remaining == 0:
                            if queue_idle_started_at is None:
                                queue_idle_started_at = asyncio.get_event_loop().time()
                            else:
                                idle_elapsed = asyncio.get_event_loop().time() - queue_idle_started_at
                                if idle_elapsed >= GPU_WORKER_COMFYUI_QUEUE_IDLE_FAIL_SECONDS:
                                    raise WorkflowExecutionError(
                                        'ComfyUI queue is empty but workflow outputs are missing. Workflow likely failed to start.'
                                    )
                        else:
                            queue_idle_started_at = None

            except OutOfMemoryError:
                raise
            except WorkflowExecutionError:
                raise
            except (aiohttp.ClientConnectorError, aiohttp.ClientOSError,
                    aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as conn_error:
                connection_failure_count += 1
                if connection_failure_started_at is None:
                    connection_failure_started_at = asyncio.get_event_loop().time()
                failure_window = asyncio.get_event_loop().time() - connection_failure_started_at
                if (
                    connection_failure_count >= GPU_WORKER_COMFYUI_CONNECTION_FAILURE_LIMIT
                    or failure_window >= GPU_WORKER_COMFYUI_SERVER_DOWN_GRACE_SECONDS
                ):
                    raise WorkflowExecutionError(
                        'Unable to reach ComfyUI server. Please verify the server status.'
                    )
            except Exception as e:
                # Log but continue
                pass

            await asyncio.sleep(2)

    async def _read_comfyui_output(self, filename: str, subfolder: str, file_type: str) -> bytes:
        """
        Download an output file using ComfyUI's HTTP view API.

        Args:
            filename: Output filename
            subfolder: Output subfolder
            file_type: ComfyUI file type, typically "output"

        Returns:
            File content as bytes
        """
        try:
            query = {
                "filename": filename,
                "subfolder": subfolder or "",
                "type": file_type or "output",
            }
            url = f"{COMFYUI_SERVER_ADDRESS}/view"
            timeout = aiohttp.ClientTimeout(total=120, connect=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=query) as response:
                    if response.status != 200:
                        error_body = (await response.text())[:500]
                        raise WorkflowExecutionError(
                            f"ComfyUI view API returned {response.status} for {filename}: {error_body}"
                        )
                    return await response.read()
        except Exception as e:
            raise WorkflowExecutionError(f"Failed to download output file {filename}: {str(e)}")

    async def _copy_comfyui_output_file(self, file_info: Dict[str, Any]) -> str:
        """
        Copy ComfyUI output file to local temp directory.

        Args:
            file_info: File info from ComfyUI output

        Returns:
            Local path to copied file
        """
        filename = file_info.get('filename') or Path(file_info.get('fullpath', '')).name
        if not filename and not file_info.get('fullpath'):
            raise WorkflowExecutionError('Missing filename in ComfyUI output')

        file_data = await self._read_comfyui_output(
            filename,
            file_info.get('subfolder', ''),
            file_info.get('type', 'output')
        )

        file_ext = Path(filename).suffix or '.bin'
        temp_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = self.tmp_dir / temp_filename

        async with aiofiles.open(temp_path, 'wb') as f:
            await f.write(file_data)

        return str(temp_path)

    def _determine_output_key(
        self,
        filename: str,
        file_type: str,
        current: Dict[str, str],
        is_image_task: bool
    ) -> Optional[str]:
        """
        Determine output key based on filename and file type.

        Args:
            filename: Output filename
            file_type: File type (images, videos, etc.)
            current: Current output mapping (to avoid duplicates)
            is_image_task: Whether this is an image generation task

        Returns:
            Output key or None if file should be skipped
        """
        normalized_filename = (filename or '').lower()

        # Only accept outputs generated for API consumption
        if not normalized_filename.startswith('jit_api'):
            return None

        # Check for keyword matches against jit_api filenames
        for keyword, mapped_key in AUDIO_OUTPUT_KEYWORDS.items():
            if normalized_filename.startswith(keyword) and mapped_key not in current:
                return mapped_key

        normalized_type = (file_type or '').lower()
        video_types = {'videos', 'video', 'gifs'}

        if is_image_task:
            if normalized_type in {'images'} and 'image_url' not in current:
                return 'image_url'
            return None

        if normalized_type in {'images'} and 'thumbnail_url' not in current:
            return 'thumbnail_url'

        if normalized_type in video_types:
            if 'upscaled_video_url' not in current:
                return 'upscaled_video_url'
            if 'upscaled_video_url' not in current:
                return 'upscaled_video_url'

        return None

    def _guess_output_key(
        self,
        filename: str,
        file_type: str,
        is_image_task: bool
    ) -> Optional[str]:
        """
        Fallback classifier when filenames do not follow jit_api prefixes.

        Args:
            filename: Output filename or path
            file_type: Output type reported by ComfyUI
            is_image_task: Whether the task is image focused

        Returns:
            Output key guess or None
        """
        ext = Path(filename).suffix.lower()
        normalized_type = (file_type or '').lower()

        video_exts = {'.mp4', '.mov', '.webm', '.gif'}
        image_exts = {'.png', '.jpg', '.jpeg', '.webp'}
        audio_exts = {'.mp3', '.wav', '.flac', '.m4a'}

        if ext in image_exts or normalized_type in {'images', 'image'}:
            return 'image_url' if is_image_task else 'thumbnail_url'

        if ext in video_exts or normalized_type in {'videos', 'video', 'gifs'}:
            return 'upscaled_video_url'

        if ext in audio_exts:
            return 'audio_url'

        return None

    async def process_outputs(
        self,
        history: Dict,
        task_type: str
    ) -> Dict[str, str]:
        """
        Process ComfyUI outputs and return ComfyUI download URLs.

        Args:
            history: ComfyUI history data with outputs
            task_type: Task type (e.g., 'image-to-video', 'text-to-image')

        Returns:
            Dictionary mapping output keys to ComfyUI /view URLs
        """
        outputs = history.get('outputs') or {}
        if not outputs:
            raise WorkflowExecutionError('ComfyUI workflow returned no outputs')

        is_image_task = task_type in ['text-to-image', 'image-to-image']

        # First pass: collect all files and group by output_key
        files_by_key: Dict[str, list] = {}

        for node_id, node_output in outputs.items():
            if not isinstance(node_output, dict):
                continue

            for file_type, file_list in node_output.items():
                normalized_list = []
                if isinstance(file_list, list):
                    normalized_list = file_list
                elif isinstance(file_list, dict):
                    dict_values = list(file_list.values()) if file_list else []
                    if dict_values and all(isinstance(value, dict) for value in dict_values):
                        normalized_list = dict_values
                    else:
                        normalized_list = [file_list]
                else:
                    continue

                for file_info in normalized_list:
                    if not isinstance(file_info, dict):
                        continue

                    origin_type = (file_info.get('type') or 'output').lower()
                    if origin_type != 'output':
                        # Skip transient/temp files
                        continue

                    filename = file_info.get('filename') or Path(file_info.get('fullpath', '')).name
                    if not filename:
                        continue

                    normalized_info = dict(file_info)
                    normalized_info.setdefault('filename', filename)

                    output_key = self._determine_output_key(filename, file_type, {}, is_image_task)
                    if not output_key:
                        output_key = self._guess_output_key(filename, file_type, is_image_task)

                    if not output_key:
                        continue

                    if output_key not in files_by_key:
                        files_by_key[output_key] = []

                    files_by_key[output_key].append((normalized_info, filename, node_id, file_type))

        # Second pass: for each output_key, select the best file (prefer -audio)
        result: Dict[str, str] = {}

        for output_key, file_candidates in files_by_key.items():
            # Prefer files with '-audio' suffix
            selected_file = None
            for file_info, filename, node_id, _file_type in file_candidates:
                if '-audio' in filename:
                    selected_file = (file_info, filename, node_id, _file_type)
                    break

            # If no audio version found, use the first file
            if not selected_file:
                selected_file = file_candidates[0]

            file_info, filename, node_id, _file_type = selected_file

            try:
                filename = file_info.get('filename') or Path(file_info.get('fullpath', '')).name
                subfolder = str(file_info.get('subfolder', '') or '')
                file_type = str(file_info.get('type', 'output') or 'output')
                if not filename:
                    raise WorkflowExecutionError('Missing filename in ComfyUI output')
                result[output_key] = (
                    f"{COMFYUI_SERVER_ADDRESS}/view?"
                    f"filename={quote(filename)}&subfolder={quote(subfolder)}&type={quote(file_type)}"
                )
            except Exception as e:
                raise WorkflowExecutionError(f"Failed to process output {filename}: {e}")

        if not result:
            raise WorkflowExecutionError('No recognizable outputs from ComfyUI workflow')

        return result

    async def execute_workflow(
        self,
        workflow_id: str,
        task_input: Dict,
        downloaded_files: Dict[str, str],
        task_type: str
    ) -> Dict[str, str]:
        """
        Execute a ComfyUI workflow and return local file paths.

        Args:
            workflow_id: Workflow identifier (e.g., 'text-to-image')
            task_input: Input parameters (e.g., {'prompt': '...', 'width': 768})
            downloaded_files: File placeholders (e.g., {'{{source_image}}': '/path/to/image.jpg'})
            task_type: Task type for output processing

        Returns:
            Dictionary mapping output keys to local file paths:
            - image_url -> local image path
            - upscaled_video_url -> local raw video path
            - thumbnail_url -> local thumbnail path
            - etc.
        """
        # Load workflow
        workflow = await self.load_workflow(workflow_id)

        # Replace placeholders
        workflow = await self.replace_placeholders(workflow, task_input, downloaded_files)

        # Queue workflow
        prompt_id, client_id = await self.queue_workflow(workflow)

        # Poll for completion
        _, history = await self.poll_completion(prompt_id, client_id)

        # Process outputs and return local paths
        return await self.process_outputs(history, task_type)
