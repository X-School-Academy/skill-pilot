from routes_shared import *

import yaml
import routes_config  # noqa: F401
import routes_codeware  # noqa: F401
import routes_integrations  # noqa: F401
import routes_file_manager  # noqa: F401
from routes_file_manager import (
    files_copy,
    files_delete,
    files_download,
    files_events,
    files_info,
    files_list,
    files_mkdir,
    files_move,
    files_read,
    files_rename,
    files_upload,
    files_write,
)

_REPO_ROOT_RESOLVED = _REPO_ROOT.resolve()
_DEV_WEBUI_SESSION_NAME = "sp-webui-dev"
_DEV_ENGINE_SESSION_NAME = "sp-engine-dev"
_EXPLORE_DEV_START_GRACE_SECONDS = 20.0


@router.get("/api/health")
def health():
    return {"status": "ok", "timestamp": time.time()}


@router.get("/api/local-dev-token")
def local_dev_token():
    return {"token": LOCAL_DEV_TOKEN}


@router.get("/api/terminal")
def terminal_api(command: str = Query("top"), session: str | None = Query(None), readonly: int = Query(0)):
    is_readonly = int(readonly or 0) == 1
    if session:
        try:
            if is_readonly:
                safe_session = _validate_tmux_session_name_any(session)
            else:
                safe_session = _validate_writable_session_name(session)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        readonly_param = "&readonly=1" if is_readonly else ""
        if is_readonly:
            attach_command = _build_tmux_attach_command_any(safe_session, readonly=True)
        else:
            attach_command = _build_tmux_attach_command_any(safe_session)
        return {
            "session": safe_session,
            "command": attach_command,
            "websocket_path": f"/api/terminal/ws?session={quote(safe_session)}{readonly_param}",
        }

    safe_command = _coerce_command(command)
    return {
        "command": safe_command,
        "websocket_path": f"/api/terminal/ws?command={quote(safe_command)}",
    }


@router.get("/api/terminal/tmux/sessions")
def terminal_tmux_sessions():
    try:
        sessions = _list_live_tmux_sessions()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "sessions": []})
    return {"sessions": sessions}


@router.get("/api/terminal/tmux/external-sessions")
def terminal_tmux_external_sessions():
    try:
        sessions = _list_external_tmux_sessions()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "sessions": []})
    return {"sessions": sessions}


@router.get("/api/session-roots")
def session_roots():
    try:
        roots = routes_file_manager._discover_file_manager_roots()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "roots": [], "has_worktrees": False})

    has_worktrees = any(str(root.get("kind") or "") == "worktree" for root in roots)
    project_root = next((root for root in roots if str(root.get("kind") or "") == "project"), None)
    return {
        "has_worktrees": has_worktrees,
        "default_path": str(project_root.get("path") if project_root else _REPO_ROOT),
        "roots": [
            {
                "value": str(root["path"]),
                "label": f"Main project: {root['label']}" if str(root.get("kind") or "") == "project" else f"Worktree: {root['label']}",
                "kind": str(root["kind"]),
            }
            for root in roots
        ],
    }


@router.post("/api/terminal/tmux/create")
def terminal_tmux_create(payload: Dict[str, Any]):
    prompt = (str(payload.get("prompt") or "")).strip()
    session_type = str(payload.get("session_type") or "").strip().lower()
    provider_id = (str(payload.get("provider_id") or "")).strip() or None
    native_terminal = _bool_with_default(payload.get("native_terminal"), False)
    provider: Dict[str, Any] | None = None
    launch_command = ""
    start_dir: Path | None = None
    start_shell = ""
    shell_session_name = ""
    sandbox = payload.get("sandbox")
    auto = payload.get("auto")
    network = payload.get("network")
    requested_start_path = payload.get("path")
    requested_path_mode = (str(payload.get("path_mode") or "").strip().lower() or None)

    try:
        start_dir = _resolve_terminal_start_dir(requested_start_path, path_mode=requested_path_mode)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    if prompt:
        provider, launch_command, command = _build_provider_command(
            provider_id=provider_id or "",
            prompt=prompt,
            sandbox=sandbox,
            auto=auto,
            network=network,
        )
        logger.info("[tmux-create] provider=%s command=%s", provider.get("id"), command)
    else:
        if session_type == "shell":
            start_shell = _resolve_system_shell()
            requested_shell_session = str(payload.get("session_name") or "").strip()
            if requested_shell_session:
                try:
                    shell_session_name = _validate_tmux_session_name_any(requested_shell_session)
                except ValueError as exc:
                    return JSONResponse(status_code=400, content={"error": str(exc)})
            launch_command = ""
            command = start_shell
            logger.info("[tmux-create] shell cwd=%s shell=%s", start_dir, start_shell)
        else:
            launch_command = _coerce_command(str(payload.get("command") or ""))
            command = launch_command
            logger.info("[tmux-create] raw command=%s", command)

    try:
        if session_type == "shell":
            session_name = _create_or_get_web_shell_tmux_session(
                start_dir or _REPO_ROOT,
                shell_path=start_shell or None,
                session_name=shell_session_name or None,
            )
            native_status = {"requested": False, "opened": False}
            attach_command = _build_tmux_attach_command_any(session_name)
        elif native_terminal:
            session_name = _create_native_tmux_session(launch_command, start_dir=start_dir)
            native_status = _open_native_terminal_for_tmux(session_name)
            attach_command = _build_tmux_attach_command_any(session_name)
        else:
            session_name = _create_webui_tmux_session(launch_command, start_dir=start_dir)
            native_status = {"requested": False, "opened": False}
            attach_command = _build_tmux_attach_command(session_name)
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    if native_terminal and "requested" not in native_status:
        native_status["requested"] = True
    if provider is not None:
        try:
            _record_tmux_agent_meta(session_name, provider, sandbox=sandbox, auto=auto, network=network)
        except Exception as exc:
            logger.warning("failed to record tmux agent meta for %s: %s", session_name, exc)

    return {
        "session": {
            "name": session_name,
            "command": command,
            "attach_command": attach_command,
            "cwd": str(start_dir or _REPO_ROOT),
            "shell": start_shell or None,
        },
        "native_terminal": native_status,
    }


@router.post("/api/terminal/tmux/kill")
def terminal_tmux_kill(payload: Dict[str, Any]):
    try:
        raw_session = str(payload.get("session") or "")
        if raw_session.strip() == WORKFLOW_EXECUTE_SESSION_NAME:
            session_name = _validate_tmux_session_name_any(raw_session)
            with _WORKFLOW_EXECUTE_LOCK:
                thread = _WORKFLOW_EXECUTE_STATE.get("thread")
            _WORKFLOW_EXECUTE_STOP.set()
            _WORKFLOW_EXECUTE_CONTINUE.set()
            removed = _kill_tmux_session_with_history(session_name)
            if thread and thread.is_alive():
                thread.join(timeout=5.0)
            if removed:
                _reset_workflow_execute_state(status="terminated")
            _WORKFLOW_EXECUTE_CONTINUE.clear()
            return {"status": "ok", "removed": removed, "session": session_name}
        session_name = _validate_tmux_session_name_any(raw_session)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    if _is_protected_tmux_session(session_name):
        return JSONResponse(status_code=403, content={"error": f"tmux session '{session_name}' is protected"})
    try:
        removed = _kill_tmux_session_with_history(session_name)
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok", "removed": removed, "session": session_name}


@router.get("/api/terminal/tmux/history")
def terminal_tmux_history(session: str):
    try:
        safe_session = _validate_tmux_session_name_any(session)
        history = _capture_tmux_pane_history_any(safe_session)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return history


@router.get("/api/terminal/tmux/saved-histories")
def terminal_tmux_saved_histories():
    try:
        histories = _list_saved_terminal_histories()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "histories": []})
    return {"histories": histories}


@router.get("/api/terminal/tmux/saved-history")
def terminal_tmux_saved_history(id: str):
    try:
        history = _read_saved_terminal_history(id)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return history


@router.delete("/api/terminal/tmux/saved-history")
def terminal_tmux_delete_saved_history(id: str):
    try:
        removed = _delete_saved_terminal_history(id)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok", "removed": removed, "id": id}


@router.post("/api/terminal/tmux/cleanup")
def terminal_tmux_cleanup():
    try:
        removed_count = _cleanup_webui_tmux_sessions()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "removed_count": 0})
    return {"status": "ok", "removed_count": removed_count}


@router.post("/api/terminal/tmux/cleanup-native-stale")
def terminal_tmux_cleanup_native_stale():
    try:
        removed_count = _cleanup_stale_native_tmux_sessions()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "removed_count": 0})
    return {"status": "ok", "removed_count": removed_count}


@router.post("/api/heartbeat")
def heartbeat():
    global _last_heartbeat_time
    _last_heartbeat_time = time.time()
    return {"status": "ok", "timestamp": _last_heartbeat_time}


def _verify_active_workflow_session() -> None:
    workflow_status = _workflow_execute_status()
    if not workflow_status.get("thread_alive"):
        return

    session_name = str(workflow_status.get("session_name") or WORKFLOW_EXECUTE_SESSION_NAME).strip() or WORKFLOW_EXECUTE_SESSION_NAME
    try:
        session_exists = _tmux_session_exists(session_name)
    except RuntimeError as exc:
        logger.warning("[workflow-execute] session_check_failed session=%s error=%s", session_name, exc)
        return
    if not session_exists:
        logger.warning(
            "[workflow-execute] session_missing session=%s status=%s",
            session_name,
            workflow_status.get("status"),
        )
        _reset_workflow_execute_state(status="terminated", error="workflow tmux session was terminated")


async def _heartbeat_watcher() -> None:
    global _last_native_cleanup_time
    while True:
        await asyncio.sleep(5)
        _verify_active_workflow_session()
        now = time.time()
        if now - _last_native_cleanup_time >= _NATIVE_STALE_CLEANUP_INTERVAL_SECONDS:
            try:
                removed = _cleanup_stale_native_tmux_sessions()
                if removed > 0:
                    logger.info("[heartbeat] cleaned up %d stale native tmux session(s)", removed)
            except Exception as exc:
                logger.warning("failed native stale tmux cleanup: %s", exc)
            _last_native_cleanup_time = now


def start_heartbeat_watcher() -> None:
    global _heartbeat_watcher_started
    if not _heartbeat_watcher_started:
        _heartbeat_watcher_started = True
        asyncio.create_task(_heartbeat_watcher())


@router.websocket("/api/terminal/ws")
async def terminal_ws(
    websocket: WebSocket,
    command: str = Query("top"),
    session: str | None = Query(None),
    cols: int = Query(120),
    rows: int = Query(30),
    binary: int = Query(0),
    readonly: int = Query(0),
):
    started_at = time.perf_counter()
    await websocket.accept()

    is_readonly = int(readonly or 0) == 1
    session_name: str | None = None
    if session:
        try:
            if is_readonly:
                session_name = _validate_tmux_session_name_any(session)
            else:
                session_name = _validate_writable_session_name(session)
        except ValueError as exc:
            await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
            await websocket.close(code=1008)
            return
        try:
            if not _tmux_session_exists(session_name):
                await websocket.send_text(json.dumps({"type": "error", "error": f"tmux session not found: {session_name}"}))
                await websocket.close(code=1008)
                return
        except RuntimeError as exc:
            await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
            await websocket.close(code=1011)
            return
        if is_readonly:
            shell_command = _build_tmux_attach_command_any(session_name, readonly=True)
        else:
            shell_command = _build_tmux_attach_command_any(session_name)
    else:
        shell_command = _coerce_command(command)

    use_binary = int(binary or 0) == 1
    initial_cols = max(20, min(int(cols or 120), 500))
    initial_rows = max(5, min(int(rows or 30), 200))
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(
        "[terminal-ws] accepted client=%s command=%s session=%s cols=%s rows=%s",
        client_host,
        shell_command,
        session_name or "",
        initial_cols,
        initial_rows,
    )
    master_fd, slave_fd = pty.openpty()
    proc: subprocess.Popen[Any] | None = None

    try:
        _set_pty_size(master_fd, initial_cols, initial_rows)
        _set_pty_size(slave_fd, initial_cols, initial_rows)
        def _child_preexec() -> None:
            # Mirror node-pty behavior: child gets a new session and controlling TTY.
            os.setsid()
            try:
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            except OSError:
                pass

        proc = subprocess.Popen(
            ["/bin/sh", "-lc", shell_command],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=False,
            preexec_fn=_child_preexec,
            env=safe_env(
                extra={
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
                "COLUMNS": str(initial_cols),
                "LINES": str(initial_rows),
                }
            ),
            close_fds=True,
        )
    except Exception as exc:
        os.close(master_fd)
        os.close(slave_fd)
        await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
        await websocket.close(code=1011)
        return
    user_input_event = asyncio.Event()
    output_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def reader() -> None:
        try:
            while True:
                chunk = await asyncio.to_thread(os.read, master_fd, 8192)
                if not chunk:
                    break
                await output_queue.put(chunk)
        except OSError:
            pass
        finally:
            await output_queue.put(None)

    async def sender() -> None:
        max_size = 262144
        flush_delay = 0.003
        buffer: list[bytes] = []
        buffered_len = 0
        image_url_cache: Dict[bytes, bytes] = {}

        async def flush() -> None:
            nonlocal buffered_len
            if not buffer:
                return
            payload = b"".join(buffer)
            buffer.clear()
            buffered_len = 0
            if TERMINAL_AUTO_IMAGE_URL_PREVIEW:
                payload = await _replace_image_urls_with_iip(payload, image_url_cache)
            if use_binary:
                await websocket.send_bytes(payload)
            else:
                await websocket.send_text(json.dumps({"type": "output", "data": payload.decode(errors="replace")}))

        while True:
            try:
                if buffer:
                    item = await asyncio.wait_for(output_queue.get(), timeout=flush_delay)
                else:
                    item = await output_queue.get()
            except asyncio.TimeoutError:
                await flush()
                continue

            if item is None:
                await flush()
                break

            buffer.append(item)
            buffered_len += len(item)
            if buffered_len >= max_size or user_input_event.is_set():
                user_input_event.clear()
                await flush()

    async def receiver() -> None:
        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                payload = {"type": "input", "data": message}
            event_type = payload.get("type")
            if event_type == "resize":
                next_cols = int(payload.get("cols") or 120)
                next_rows = int(payload.get("rows") or 30)
                _set_pty_size(master_fd, next_cols, next_rows)
                _set_pty_size(slave_fd, next_cols, next_rows)
                _notify_sigwinch(master_fd, proc)
                continue
            if event_type == "input":
                if is_readonly:
                    continue
                data = str(payload.get("data") or "")
                if data:
                    await asyncio.to_thread(os.write, master_fd, data.encode())
                    user_input_event.set()
                continue
            if event_type == "close":
                break

    reader_task = asyncio.create_task(reader())
    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())

    try:
        done, pending = await asyncio.wait(
            [reader_task, sender_task, receiver_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, (WebSocketDisconnect, asyncio.CancelledError)):
                raise exc
    except WebSocketDisconnect:
        pass
    finally:
        if proc is not None:
            await _terminate_process(proc)
        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            os.close(slave_fd)
        except OSError:
            pass
        try:
            await websocket.close()
        except RuntimeError:
            pass
        if session_name and session_name.startswith(TMUX_SESSION_PREFIX):
            try:
                removed = _cleanup_webui_tmux_session(session_name)
                if removed:
                    logger.info("[terminal-ws] cleaned up tmux session %s on websocket close", session_name)
            except RuntimeError as exc:
                logger.warning("[terminal-ws] failed to cleanup tmux session %s: %s", session_name, exc)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "[terminal-ws] closed client=%s command=%s session=%s elapsed_ms=%s",
            client_host,
            shell_command,
            session_name or "",
            elapsed_ms,
        )

def _safe_tasks_path(task_path: str, *, must_exist: bool = True) -> Path:
    if not task_path:
        raise ValueError("Missing task path")
    candidate = (TASKS_DIR / task_path).resolve()
    if candidate != TASKS_DIR and TASKS_DIR not in candidate.parents:
        raise ValueError("Invalid task path")
    if must_exist and (not candidate.exists() or not candidate.is_file()):
        raise FileNotFoundError("Task not found")
    return candidate


def _normalize_task_slug(value: str, *, default: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return normalized or default


def _normalize_task_folder_name(value: str) -> str:
    if not value:
        return ""
    return _normalize_task_slug(value, default="task")


def _normalize_task_file_name(value: str) -> str:
    raw_name = (value or "").strip()
    suffix = Path(raw_name).suffix.lower()
    stem = raw_name[:-len(suffix)] if suffix else raw_name
    safe_stem = _normalize_task_slug(stem, default="new-task")
    safe_suffix = suffix if suffix not in {"", "."} else ".md"
    return f"{safe_stem}{safe_suffix}"


def _task_instruction_project_path(task_path: str) -> str:
    trimmed = str(task_path or "").strip().replace("\\", "/").lstrip("/")
    return f"workspace/tasks/{trimmed}" if trimmed else "workspace/tasks"


def _task_workflow_project_path(workflow_path: str) -> str:
    trimmed = str(workflow_path or "").strip().replace("\\", "/").lstrip("/")
    if trimmed.startswith("core/workflows/"):
        return trimmed
    return f"core/workflows/{trimmed}" if trimmed else "core/workflows"


def _task_workflow_output_dir(
    task_path: str,
    workflow_path: str,
    reference_file_paths: list[str] | None = None,
) -> tuple[str, Path]:
    return workflow_task_output_dir(
        _terminal_workflow_base_dir(),
        _task_instruction_project_path(task_path),
        _task_workflow_project_path(workflow_path),
        repo_root=_REPO_ROOT,
        reference_file_paths=reference_file_paths,
    )


def _unique_task_file_path(parent: Path, file_name: str) -> Path:
    candidate = parent / file_name
    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while candidate.exists():
        candidate = parent / f"{stem}_{index}{suffix}"
        index += 1
    return candidate


def _unique_task_dir_path(folder_name: str) -> Path:
    candidate = TASKS_DIR / folder_name
    index = 1
    while candidate.exists():
        candidate = TASKS_DIR / f"{folder_name}_{index}"
        index += 1
    return candidate


def _safe_media_path(media_path: str, *, must_exist: bool = True) -> Path:
    if not media_path:
        raise ValueError("Missing media path")
    candidate = (MEDIA_DIR / media_path).resolve()
    if candidate != MEDIA_DIR and MEDIA_DIR not in candidate.parents:
        raise ValueError("Invalid media path")
    if must_exist and (not candidate.exists() or not candidate.is_file()):
        raise FileNotFoundError("Media not found")
    return candidate


def _media_instruction_project_path(media_path: str) -> str:
    trimmed = str(media_path or "").strip().replace("\\", "/").lstrip("/")
    return f"workspace/media/{trimmed}" if trimmed else "workspace/media"


def _unique_media_dir_path(folder_name: str) -> Path:
    candidate = MEDIA_DIR / folder_name
    index = 1
    while candidate.exists():
        candidate = MEDIA_DIR / f"{folder_name}_{index}"
        index += 1
    return candidate


def _safe_vibe_coding_path(task_path: str, *, must_exist: bool = True) -> Path:
    if not task_path:
        raise ValueError("Missing vibe coding path")
    candidate = (VIBE_CODING_DIR / task_path).resolve()
    if candidate != VIBE_CODING_DIR and VIBE_CODING_DIR not in candidate.parents:
        raise ValueError("Invalid vibe coding path")
    if must_exist and (not candidate.exists() or not candidate.is_file()):
        raise FileNotFoundError("Vibe coding file not found")
    return candidate


def _normalize_vibe_project_name(value: str) -> str:
    return _normalize_task_slug(value, default="project")


VIBE_CODING_DESIGN_DOCS_DIR = "design-docs"
VIBE_CODING_ARCHIVE_DIR = "archive"
VIBE_CODING_ASSETS_DIR = "assets"
VIBE_CODING_ICON_FILE = "icon.png"
VIBE_CODING_INFO_FILE = "info.yaml"
VIBE_CODING_COMMAND_KEYS = ("start", "dev", "build", "stop")


def _vibe_instruction_project_path(task_path: str) -> str:
    trimmed = str(task_path or "").strip().replace("\\", "/").lstrip("/")
    return f"workspace/vibe-coding/{trimmed}" if trimmed else "workspace/vibe-coding"


def _unique_vibe_project_dir_path(project_name: str) -> Path:
    candidate = VIBE_CODING_DIR / project_name
    index = 1
    while candidate.exists():
        candidate = VIBE_CODING_DIR / f"{project_name}_{index}"
        index += 1
    return candidate


def _ensure_vibe_project_file(project_name: str, file_name: str) -> tuple[Path, Path, str]:
    normalized_project = _normalize_vibe_project_name(project_name)
    if not normalized_project:
        raise ValueError("Project name is required")
    project_dir = VIBE_CODING_DIR / normalized_project
    project_dir.mkdir(parents=True, exist_ok=True)
    design_docs_dir = project_dir / VIBE_CODING_DESIGN_DOCS_DIR
    design_docs_dir.mkdir(parents=True, exist_ok=True)
    (design_docs_dir / VIBE_CODING_ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)
    file_path = design_docs_dir / file_name
    return project_dir, file_path, normalized_project


def _vibe_project_root_for_file(file_path: Path) -> Path:
    try:
        relative_parts = file_path.relative_to(VIBE_CODING_DIR).parts
    except ValueError as exc:
        raise ValueError("Invalid project file") from exc
    if not relative_parts:
        raise ValueError("Invalid project file")
    return VIBE_CODING_DIR / relative_parts[0]


def _is_vibe_project_requirements_file(file_path: Path) -> bool:
    try:
        relative_parts = file_path.relative_to(VIBE_CODING_DIR).parts
    except ValueError:
        return False
    return (
        len(relative_parts) == 3
        and relative_parts[1] == VIBE_CODING_DESIGN_DOCS_DIR
        and relative_parts[2] == "requirements.md"
    )


def _remove_project_dir(project_dir: Path) -> None:
    if project_dir == VIBE_CODING_DIR or VIBE_CODING_DIR not in project_dir.parents:
        raise ValueError("Invalid project directory")
    shutil.rmtree(project_dir)


def _title_from_vibe_project_name(project_name: str) -> str:
    words = [part for part in re.split(r"[-_\s]+", project_name.strip()) if part]
    if not words:
        return project_name or "Project"
    return " ".join(word[:1].upper() + word[1:] for word in words)


def _initials_from_vibe_project_name(project_name: str) -> str:
    parts = [part for part in project_name.split("-") if part]
    if not parts:
        parts = [part for part in re.split(r"[_\s]+", project_name) if part]
    return "".join(part[:1].upper() for part in parts[:3]) or "?"


def _read_vibe_project_info(info_path: Path) -> Dict[str, Any]:
    if not info_path.exists() or not info_path.is_file():
        return {}
    try:
        loaded = yaml.safe_load(info_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("failed to read vibe coding project info %s: %s", info_path, exc)
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _vibe_project_summary(project_dir: Path) -> Dict[str, Any] | None:
    if not project_dir.is_dir() or project_dir.name.startswith("."):
        return None
    assets_dir = project_dir / VIBE_CODING_ASSETS_DIR
    info = _read_vibe_project_info(assets_dir / VIBE_CODING_INFO_FILE)
    raw_commands = info.get("commands") if isinstance(info.get("commands"), dict) else {}
    commands = {
        key: str(raw_commands.get(key) or "").strip()
        for key in VIBE_CODING_COMMAND_KEYS
    }
    icon_path = assets_dir / VIBE_CODING_ICON_FILE
    relative_icon = None
    if icon_path.exists() and icon_path.is_file():
        relative_icon = str(icon_path.relative_to(VIBE_CODING_DIR))
    display_name = str(info.get("display_name") or "").strip()
    return {
        "name": project_dir.name,
        "path": str(project_dir.relative_to(VIBE_CODING_DIR)),
        "display_name": display_name or _title_from_vibe_project_name(project_dir.name),
        "initials": _initials_from_vibe_project_name(project_dir.name),
        "icon_path": relative_icon,
        "commands": commands,
        "mtime": project_dir.stat().st_mtime,
    }


def _safe_research_path(task_path: str, *, must_exist: bool = True) -> Path:
    if not task_path:
        raise ValueError("Missing research path")
    candidate = (RESEARCH_DIR / task_path).resolve()
    if candidate != RESEARCH_DIR and RESEARCH_DIR not in candidate.parents:
        raise ValueError("Invalid research path")
    if must_exist and (not candidate.exists() or not candidate.is_file()):
        raise FileNotFoundError("Research file not found")
    return candidate


def _normalize_research_topic_name(value: str) -> str:
    return _normalize_task_slug(value, default="topic")


def _unique_research_topic_dir_path(topic_name: str) -> Path:
    candidate = RESEARCH_DIR / topic_name
    index = 1
    while candidate.exists():
        candidate = RESEARCH_DIR / f"{topic_name}_{index}"
        index += 1
    return candidate


def _safe_skill_pilot_development_path(task_path: str, *, must_exist: bool = True) -> Path:
    if not task_path:
        raise ValueError("Missing development path")
    candidate = (SKILL_PILOT_DEVELOPMENT_DIR / task_path).resolve()
    if candidate != SKILL_PILOT_DEVELOPMENT_DIR and SKILL_PILOT_DEVELOPMENT_DIR not in candidate.parents:
        raise ValueError("Invalid development path")
    if must_exist and (not candidate.exists() or not candidate.is_file()):
        raise FileNotFoundError("Development file not found")
    return candidate


def _normalize_skill_pilot_feature_name(value: str) -> str:
    return _normalize_task_slug(value, default="feature")


def _unique_skill_pilot_feature_dir_path(feature_name: str) -> Path:
    candidate = SKILL_PILOT_DEVELOPMENT_DIR / feature_name
    index = 1
    while candidate.exists():
        candidate = SKILL_PILOT_DEVELOPMENT_DIR / f"{feature_name}_{index}"
        index += 1
    return candidate


def _skill_pilot_feature_catalog() -> list[dict[str, str]]:
    if not FEATURES_DIR.exists():
        return []
    items: list[dict[str, str]] = []
    for file_path in sorted(FEATURES_DIR.glob("*.md")):
        items.append({"name": file_path.stem, "path": str(file_path.relative_to(_REPO_ROOT))})
    return items


def _append_related_feature_references(content: str, related_features: list[str]) -> str:
    cleaned = [item.strip() for item in related_features if item.strip()]
    body = content.rstrip()
    if not cleaned:
        return f"{body}\n" if body else ""
    lines = [
        "The related feature files for reference:",
        *[f"- {item}" for item in cleaned],
    ]
    appendix = "\n".join(lines)
    if not body:
        return f"{appendix}\n"
    return f"{body}\n\n{appendix}\n"


def _extract_task_create_parts(payload: Dict[str, Any]) -> tuple[str, str]:
    folder = str(payload.get("folder") or "").strip()
    file_name = str(payload.get("file") or "").strip()

    if folder and any(sep in folder for sep in ("/", "\\")):
        raise ValueError("Task folder supports only one subfolder level")
    if file_name and any(sep in file_name for sep in ("/", "\\")):
        raise ValueError("File name cannot include folder separators")

    if file_name:
        return folder, file_name

    raw_path = str(payload.get("path") or "").strip().replace("\\", "/")
    if not raw_path:
        raise ValueError("Task file name is required")
    if raw_path.endswith("/"):
        raise ValueError("Task path must include a filename")

    parts = [part for part in raw_path.strip("/").split("/") if part]
    if not parts:
        raise ValueError("Task file name is required")
    if len(parts) > 2:
        raise ValueError("Only root files or one subfolder are supported")
    if len(parts) == 1:
        return "", parts[0]
    return parts[0], parts[1]


def _is_http_url(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("http://") or lower.startswith("https://")


def _normalize_repo_relative_path(raw_path: Any) -> str:
    value = str(raw_path or "").strip().replace("\\", "/")
    value = value.lstrip("/")
    if not value:
        raise ValueError("Path cannot be empty")
    candidate = (_REPO_ROOT / value).resolve()
    if candidate != _REPO_ROOT and _REPO_ROOT not in candidate.parents:
        raise ValueError("Path must stay within the repository")
    return value


def _download_url_for_repo_path(raw_path: str) -> str:
    normalized = _normalize_repo_relative_path(raw_path)
    return f"/api/files/download?path={quote('/' + normalized)}"


def _normalize_showcase_media(value: Any) -> Dict[str, Any]:
    raw = str(value or "").strip()
    if not raw:
        return {"value": None, "url": None, "is_external": False, "is_media": False}
    is_external = _is_http_url(raw)
    if is_external:
        url = raw
        kind_path = raw
    elif raw.startswith("/"):
        # Absolute URL path served by the webui (e.g. Next.js public/ assets like "/showcases/foo.png").
        url = raw
        kind_path = raw
    else:
        url = _download_url_for_repo_path(raw)
        kind_path = "/" + raw
    kind = _task_type_from_path(kind_path)
    return {
        "value": raw,
        "url": url,
        "is_external": is_external,
        "is_media": kind in {"image", "audio", "video"},
    }


def _normalize_showcase_link(item: Any) -> Dict[str, str]:
    if not isinstance(item, dict):
        raise ValueError("Showcase link entries must be objects")
    name = str(item.get("name") or "").strip()
    url = str(item.get("url") or "").strip()
    if not name or not url:
        raise ValueError("Showcase links require name and url")
    return {"name": name, "url": url}


def _repo_relative_if_inside(path: Path) -> str | None:
    candidate = path.resolve()
    if candidate != _REPO_ROOT and _REPO_ROOT not in candidate.parents:
        return None
    return candidate.relative_to(_REPO_ROOT).as_posix()


def _resolve_showcase_skill_path(name: str) -> str | None:
    value = str(name or "").strip().strip("/")
    if not value:
        return None
    direct = (_REPO_ROOT / value).resolve()
    if direct.is_dir():
        rel = _repo_relative_if_inside(direct)
        if rel and (rel.startswith("core/skills/") or rel.startswith("dev-swarm/skills/")):
            return rel

    skill_name = value.split("/")[-1]
    for parent in (_REPO_ROOT / "core" / "skills").glob("*"):
        candidate = parent / skill_name
        if candidate.is_dir():
            return candidate.relative_to(_REPO_ROOT).as_posix()
    candidate = _REPO_ROOT / "dev-swarm" / "skills" / skill_name
    if candidate.is_dir():
        return candidate.relative_to(_REPO_ROOT).as_posix()
    return None


_SHOWCASE_TEXT_EXTENSIONS = {
    ".bash",
    ".cjs",
    ".css",
    ".cts",
    ".dart",
    ".go",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".json5",
    ".jsx",
    ".kt",
    ".md",
    ".mjs",
    ".mts",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
    ".zsh",
}


def _is_showcase_text_file(path: Path, rel_path: str) -> bool:
    if not path.is_file():
        return False
    if rel_path.startswith("core/bin/"):
        return True
    return path.suffix.lower() in _SHOWCASE_TEXT_EXTENSIONS


def _resolve_showcase_text_path(raw_path: str) -> str | None:
    try:
        rel_path = _normalize_repo_relative_path(raw_path)
    except ValueError:
        return None
    candidate = (_REPO_ROOT / rel_path).resolve()
    if not _is_showcase_text_file(candidate, rel_path):
        return None
    return rel_path


def _showcase_item(label: str, path: str | None = None) -> Dict[str, str | None]:
    return {"label": label, "path": path}


def _normalize_showcase_related(item: Any) -> Dict[str, str]:
    if not isinstance(item, dict):
        raise ValueError("Showcase related entries must be objects")
    slug = str(item.get("slug") or "").strip()
    caption = str(item.get("caption") or "").strip()
    if not slug or not caption:
        raise ValueError("Showcase related entries require slug and caption")
    return {"slug": slug, "caption": caption}


def _normalize_showcase_variant(item: Any) -> Dict[str, str]:
    if not isinstance(item, dict):
        raise ValueError("Showcase variant entries must be objects")
    slug = str(item.get("slug") or "").strip()
    caption = str(item.get("caption") or "").strip()
    if not slug or not caption:
        raise ValueError("Showcase variant entries require slug and caption")
    return {"slug": slug, "caption": caption}


def _normalize_showcase_sequence_link(item: Any, field_name: str) -> Dict[str, str] | None:
    if item in (None, ""):
        return None
    if not isinstance(item, dict):
        raise ValueError(f"Showcase {field_name} must be an object")
    slug_id = str(item.get("slug_id") or "").strip()
    title = str(item.get("title") or "").strip()
    if not slug_id or not title:
        raise ValueError(f"Showcase {field_name} requires slug_id and title")
    return {"slug_id": slug_id, "title": title}


def _normalize_showcase_repo_paths(items: Any) -> List[str]:
    if items in (None, ""):
        return []
    if not isinstance(items, list):
        raise ValueError("Showcase path lists must be arrays")
    values: List[str] = []
    for item in items:
        values.append(_normalize_repo_relative_path(item))
    return values


def _normalize_showcase_extensions(items: Any) -> List[str]:
    if items in (None, ""):
        return []
    if not isinstance(items, list):
        raise ValueError("Showcase extensions must be arrays")
    values: List[str] = []
    for item in items:
        name = str(item).strip()
        if name:
            values.append(name)
    return values


def _normalize_showcase_in_mode(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "dev":
        return "dev"
    return "prod"


def _normalize_showcase_sample(sample: Any, category_name: str) -> Dict[str, Any]:
    if not isinstance(sample, dict):
        raise ValueError(f"Sample entries for category '{category_name}' must be objects")

    sample_id = str(sample.get("id") or "").strip()
    title = str(sample.get("title") or "").strip()
    description = str(sample.get("description") or "").strip()
    prompt = str(sample.get("prompt") or "")
    if not sample_id or not title or not description or not prompt:
        raise ValueError(f"Showcase sample in '{category_name}' is missing id/title/description/prompt")

    thumbnail = _normalize_showcase_media(sample.get("thumbnail"))
    video = _normalize_showcase_media(sample.get("video"))
    tutorial = _normalize_showcase_media(sample.get("tutorial"))
    request = _normalize_showcase_media(sample.get("request"))
    git_tag = sample.get("git_tag")
    if git_tag is not None:
        git_tag = str(git_tag).strip() or None
    in_mode = _normalize_showcase_in_mode(sample.get("in_mode"))
    workflow = str(sample.get("workflow") or "").strip() or None
    directory = str(sample.get("directory") or "").strip() or None
    use_worktree = _bool_with_default(sample.get("use_worktree"), False)

    skills = _normalize_showcase_repo_paths(sample.get("skills"))
    tools = _normalize_showcase_repo_paths(sample.get("tools"))
    files = _normalize_showcase_repo_paths(sample.get("files"))
    skill_items = [_showcase_item(skill, _resolve_showcase_skill_path(skill)) for skill in skills]
    tool_items = [_showcase_item(tool, _resolve_showcase_text_path(tool)) for tool in tools]
    file_items = [_showcase_item(file_path, _resolve_showcase_text_path(file_path)) for file_path in files]
    extensions = _normalize_showcase_extensions(sample.get("extensions"))
    links = [_normalize_showcase_link(item) for item in (sample.get("links") or [])]
    related = [_normalize_showcase_related(item) for item in (sample.get("related") or [])]
    variants = [_normalize_showcase_variant(item) for item in (sample.get("variants") or [])]
    previous_showcase = _normalize_showcase_sequence_link(sample.get("previous_showcase"), "previous_showcase")
    next_showcase = _normalize_showcase_sequence_link(sample.get("next_showcase"), "next_showcase")

    goals = str(sample.get("goals") or "").strip() or None
    terms_raw = sample.get("terms")
    terms: List[str] = []
    if isinstance(terms_raw, list):
        terms = [str(t).strip() for t in terms_raw if str(t).strip()]

    try:
        popularity = int(sample.get("popularity", 0))
        level = int(sample.get("level", 1))
        rate = float(sample.get("rate", 0))
    except Exception as exc:
        raise ValueError(f"Invalid numeric showcase fields for sample '{sample_id}'") from exc

    if git_tag and not use_worktree:
        raise ValueError(f"Showcase sample '{sample_id}' must use use_worktree=true when git_tag is set")
    if git_tag and in_mode != "dev":
        raise ValueError(f"Showcase sample '{sample_id}' must use in_mode=dev when git_tag is set")
    if use_worktree and in_mode != "dev":
        raise ValueError(f"Showcase sample '{sample_id}' must use in_mode=dev when use_worktree is true")

    return {
        "id": sample_id,
        "title": title,
        "description": description,
        "thumbnail": thumbnail["value"],
        "thumbnail_url": thumbnail["url"],
        "video": video["value"],
        "video_url": video["url"],
        "tutorial": tutorial["value"],
        "tutorial_url": tutorial["url"],
        "tutorial_is_external": tutorial["is_external"],
        "tutorial_is_media": tutorial["is_media"],
        "request": request["value"],
        "request_url": request["url"],
        "request_is_media": request["is_media"],
        "prompt": prompt,
        "workflow": workflow,
        "directory": directory,
        "in_mode": in_mode,
        "git_tag": git_tag,
        "use_worktree": use_worktree,
        "skills": skills,
        "skill_items": skill_items,
        "extensions": extensions,
        "tools": tools,
        "tool_items": tool_items,
        "files": files,
        "file_items": file_items,
        "links": links,
        "related": related,
        "variants": variants,
        "previous_showcase": previous_showcase,
        "next_showcase": next_showcase,
        "goals": goals,
        "terms": terms,
        "popularity": popularity,
        "level": level,
        "rate": rate,
    }


def _normalize_showcase_category(raw_category: Any) -> Dict[str, Any]:
    if not isinstance(raw_category, dict):
        raise ValueError("Showcase categories must be objects")
    category_id = str(raw_category.get("id") or "").strip()
    category_name = str(raw_category.get("category") or "").strip()
    description = str(raw_category.get("description") or "").strip()
    if not category_name or not description:
        raise ValueError("Showcase categories require category and description")
    thumbnail = _normalize_showcase_media(raw_category.get("thumbnail"))
    
    samples = []
    samples_raw = raw_category.get("samples")
    if samples_raw is not None:
        if not isinstance(samples_raw, list):
            raise ValueError(f"Category '{category_name}' samples must be an array")
        samples = [_normalize_showcase_sample(sample, category_name) for sample in samples_raw]
        
    subcategories = []
    subcategories_raw = raw_category.get("subcategories")
    if subcategories_raw is not None:
        if not isinstance(subcategories_raw, list):
            raise ValueError(f"Category '{category_name}' subcategories must be an array")
        subcategories = [_normalize_showcase_category(sub) for sub in subcategories_raw]
        
    return {
        "id": category_id,
        "category": category_name,
        "description": description,
        "thumbnail": thumbnail["value"],
        "thumbnail_url": thumbnail["url"],
        "samples": samples,
        "subcategories": subcategories,
    }


def _validate_showcase_reference_targets(categories: List[Dict[str, Any]], field_name: str) -> None:
    samples: List[Dict[str, Any]] = []

    def collect(cat_list: List[Dict[str, Any]]) -> None:
        for category in cat_list:
            samples.extend(category.get("samples", []))
            collect(category.get("subcategories") or [])

    collect(categories)
    sample_ids = {str(sample.get("id") or "") for sample in samples}
    for sample in samples:
        sample_id = str(sample.get("id") or "")
        for item in sample.get(field_name, []):
            slug = str(item.get("slug") or "")
            if slug not in sample_ids:
                raise ValueError(f"Showcase sample '{sample_id}' has unknown {field_name} slug '{slug}'")


def _validate_showcase_sequence_targets(categories: List[Dict[str, Any]]) -> None:
    samples: List[Dict[str, Any]] = []

    def collect(cat_list: List[Dict[str, Any]]) -> None:
        for category in cat_list:
            samples.extend(category.get("samples", []))
            collect(category.get("subcategories") or [])

    collect(categories)
    sample_ids = {str(sample.get("id") or "") for sample in samples}
    for sample in samples:
        sample_id = str(sample.get("id") or "")
        for field_name in ("previous_showcase", "next_showcase"):
            item = sample.get(field_name)
            if not item:
                continue
            slug_id = str(item.get("slug_id") or "")
            if slug_id not in sample_ids:
                raise ValueError(f"Showcase sample '{sample_id}' has unknown {field_name} slug_id '{slug_id}'")


def _load_showcases() -> List[Dict[str, Any]]:
    if not _SHOWCASES_PATH.is_file():
        raise FileNotFoundError(f"Showcases file not found: {_SHOWCASES_PATH}")
    raw = json5.loads(_SHOWCASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Showcases data must be an array of categories")
        
    import yaml
    def populate_samples(categories, parent_dir):
        for cat in categories:
            cat_id = cat.get("id")
            if not cat_id:
                continue
            cat_dir = parent_dir / str(cat_id)
            samples = []
            if cat_dir.is_dir():
                files = [p for p in cat_dir.iterdir() if p.is_file() and p.name.endswith(".yaml")]
                files.sort(key=lambda x: x.name)
                for fpath in files:
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            sample = yaml.safe_load(f)
                            if isinstance(sample, dict):
                                samples.append(sample)
                    except Exception as e:
                        logger.warning(f"Failed to load showcase sample {fpath}: {e}")
            cat["samples"] = samples
            
            if cat.get("subcategories") and isinstance(cat["subcategories"], list):
                populate_samples(cat["subcategories"], cat_dir)
                
    populate_samples(raw, _SHOWCASES_PATH.parent / "showcases")

    categories = [_normalize_showcase_category(cat) for cat in raw]
    _validate_showcase_reference_targets(categories, "related")
    _validate_showcase_reference_targets(categories, "variants")
    _validate_showcase_sequence_targets(categories)
    return categories


def _find_showcase_sample(categories: List[Dict[str, Any]], sample_id: str) -> Dict[str, Any]:
    target = str(sample_id or "").strip()
    if not target:
        raise ValueError("sample_id is required")

    def _search_categories(cats: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        for category in cats:
            for sample in category.get("samples", []):
                if sample.get("id") == target:
                    return sample
            if category.get("subcategories"):
                found = _search_categories(category["subcategories"])
                if found:
                    return found
        return None

    found = _search_categories(categories)
    if found:
        return found
    raise FileNotFoundError(f"Showcase sample not found: {target}")


from worktree_utils import (
    create_worktree as _wt_create_worktree,
    git_command as _git_command,
    remove_worktree as _wt_remove_worktree,
    sanitize_worktree_suffix as _sanitize_worktree_suffix,
    worktree_path_for_suffix as _wt_path_for_suffix,
)


def _explore_worktree_path(sample_id: str) -> Path:
    return _wt_path_for_suffix(_sanitize_worktree_suffix(sample_id))


def _explore_tmux_session_exists() -> bool:
    return _tmux_session_exists(_DEV_WEBUI_SESSION_NAME) and _tmux_session_exists(_DEV_ENGINE_SESSION_NAME)


def _managed_explore_dev_snapshot() -> Dict[str, Any]:
    with _EXPLORE_TEMPLATE_LOCK:
        return dict(_EXPLORE_MANAGED_DEV)


def _set_managed_explore_dev(*, worktree_path: str, launch_id: str, started_at: float) -> None:
    with _EXPLORE_TEMPLATE_LOCK:
        _EXPLORE_MANAGED_DEV.update(
            {
                "session_name": _DEV_ENGINE_SESSION_NAME,
                "worktree_path": worktree_path,
                "launch_id": launch_id,
                "started_at": started_at,
            }
        )


def _clear_managed_explore_dev() -> None:
    with _EXPLORE_TEMPLATE_LOCK:
        _EXPLORE_MANAGED_DEV.update(
            {
                "session_name": _DEV_ENGINE_SESSION_NAME,
                "worktree_path": "",
                "launch_id": "",
                "started_at": 0.0,
            }
        )


def _store_explore_launch(launch_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with _EXPLORE_TEMPLATE_LOCK:
        _EXPLORE_TEMPLATE_LAUNCHES[launch_id] = payload
        return dict(payload)


def _update_explore_launch(launch_id: str, **updates: Any) -> Dict[str, Any] | None:
    with _EXPLORE_TEMPLATE_LOCK:
        launch = _EXPLORE_TEMPLATE_LAUNCHES.get(launch_id)
        if not launch:
            return None
        launch.update(updates)
        return dict(launch)


def _get_explore_launch(launch_id: str) -> Dict[str, Any] | None:
    with _EXPLORE_TEMPLATE_LOCK:
        launch = _EXPLORE_TEMPLATE_LAUNCHES.get(launch_id)
        return dict(launch) if launch else None


def _build_explore_launch_payload(
    *,
    launch_id: str,
    sample_id: str,
    use_worktree: bool,
    worktree_path: Path,
    target_url: str,
) -> Dict[str, Any]:
    return {
        "status": "pending",
        "launch_id": launch_id,
        "sample_id": sample_id,
        "use_worktree": use_worktree,
        "worktree_path": str(worktree_path),
        "target_url": target_url,
        "monitor_url": _explore_dev_base_url(),
        "session_name": _DEV_ENGINE_SESSION_NAME,
        "created_at": time.time(),
        "startup_log_path": str(worktree_path / ".skillpilot" / "temp" / "explore-dev-start.log"),
        "error": "",
    }


def _explore_dev_base_url() -> str:
    host, port = get_service_host_port("webui", mode="development", default_host="127.0.0.1", default_port=3003)
    return f"http://{host}:{port}"


def _explore_dev_health_url() -> str:
    return f"{_explore_dev_base_url()}/api/health"


def _probe_explore_dev_ready() -> bool:
    req = urllib.request.Request(_explore_dev_health_url(), headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=1.5) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return not payload or payload.get("status") == "ok"
    except Exception:
        return False


def _run_skillpilot_command(args: List[str], *, cwd: Path, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["./skillpilot.sh", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=False,
        env=safe_env(),
        timeout=timeout,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(message or f"skillpilot command failed: {' '.join(args)}")
    return proc


def _git_common_repo_root(repo_path: Path) -> Path:
    try:
        proc = _git_command(["rev-parse", "--git-common-dir"], cwd=repo_path)
    except Exception:
        return repo_path.resolve()
    raw = proc.stdout.strip()
    if not raw:
        return repo_path.resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (repo_path / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if candidate.name == ".git" and candidate.parent.is_dir():
        return candidate.parent.resolve()
    return repo_path.resolve()


def _spawn_skillpilot_dev_start(target_root: Path) -> None:
    log_dir = target_root / ".skillpilot" / "temp"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "explore-dev-start.log"
    with log_path.open("ab") as log_file:
        subprocess.Popen(
            ["./skillpilot.sh", "start", "--dev", "--source", "webui"],
            cwd=str(target_root),
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=safe_env(),
            start_new_session=True,
            close_fds=True,
        )


def _remove_explore_worktree(path: Path) -> None:
    _wt_remove_worktree(path)


def _explore_branch_name(sample_suffix: str) -> str:
    timestamp = int(time.time())
    return f"codex/explore-{sample_suffix}-{timestamp}"


def _create_explore_worktree(path: Path, *, sample_id: str, base_ref: str | None = None) -> None:
    sample_suffix = _sanitize_worktree_suffix(sample_id)
    branch_name = _explore_branch_name(sample_suffix)
    _wt_create_worktree(path, branch_name=branch_name, base_ref=base_ref)


def _ensure_explore_worktree(path: Path, *, sample_id: str, existing_action: str | None, base_ref: str | None = None) -> Dict[str, Any] | None:
    if path.exists():
        if existing_action not in {"continue", "remove"}:
            return {
                "status": "needs_existing_worktree_action",
                "worktree_path": str(path),
            }
        if existing_action == "remove":
            _remove_explore_worktree(path)
            _create_explore_worktree(path, sample_id=sample_id, base_ref=base_ref)
        return None
    _create_explore_worktree(path, sample_id=sample_id, base_ref=base_ref)
    return None


def _build_prompt_target_url(base_url: str, prompt: str, path: str | None = None) -> str:
    encoded_prompt = quote(prompt, safe="")
    if path:
        encoded_path = quote(path, safe="")
        return f"{base_url}/?new_session=true&prompt={encoded_prompt}&path={encoded_path}"
    return f"{base_url}/?new_session=true&prompt={encoded_prompt}"


def _stop_managed_explore_dev_if_running() -> None:
    snapshot = _managed_explore_dev_snapshot()
    if snapshot.get("worktree_path"):
        worktree_path = Path(str(snapshot["worktree_path"]))
        if worktree_path.is_dir():
            try:
                _run_skillpilot_command(["stop", "--dev"], cwd=worktree_path, timeout=90.0)
            except Exception:
                pass
    _clear_managed_explore_dev()


def _start_explore_dev_session(worktree_path: Path) -> None:
    _spawn_skillpilot_dev_start(worktree_path)


@router.get("/api/explore/showcases")
def explore_showcases():
    try:
        categories = _load_showcases()
        return {
            "categories": categories,
            "runtime_mode": get_runtime_mode(),
            "can_use_template": True,
            "managed_dev": _managed_explore_dev_snapshot(),
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "categories": []})


@router.post("/api/explore/template/start")
def explore_template_start(payload: Dict[str, Any]):
    sample_id = str(payload.get("sample_id") or "").strip()
    use_worktree = _bool_with_default(payload.get("use_worktree"), False)
    checkout_tag = _bool_with_default(payload.get("checkout_tag"), True)
    start_in_dev_mode = _bool_with_default(payload.get("start_in_dev_mode"), False)
    existing_worktree_action = str(payload.get("existing_worktree_action") or "").strip().lower() or None
    running_dev_action = str(payload.get("running_dev_action") or "").strip().lower() or None

    try:
        categories = _load_showcases()
        sample = _find_showcase_sample(categories, sample_id)
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"status": "error", "error": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(exc)})

    prompt = str(sample.get("prompt") or "")
    sample_in_mode = _normalize_showcase_in_mode(sample.get("in_mode"))
    runtime_mode = get_runtime_mode()
    current_runtime_root = _REPO_ROOT.resolve()
    dev_runtime_target_root = current_runtime_root
    if runtime_mode == "development":
        use_worktree = False
        checkout_tag = False
        dev_runtime_target_root = _git_common_repo_root(current_runtime_root)
    should_use_dev_instance = sample_in_mode == "dev" or use_worktree
    start_in_dev_mode = True if should_use_dev_instance else start_in_dev_mode

    if sample_in_mode == "dev" and not start_in_dev_mode:
        return JSONResponse(status_code=400, content={"status": "error", "error": "Dev-mode samples cannot be started in prod mode"})

    if runtime_mode == "development":
        if dev_runtime_target_root != current_runtime_root:
            try:
                _spawn_skillpilot_dev_start(dev_runtime_target_root)
            except Exception as exc:
                return JSONResponse(status_code=500, content={"status": "error", "error": str(exc)})
            return {
                "status": "relaunching_current_dev",
                "target_url": _build_prompt_target_url("", prompt),
                "sample_id": sample_id,
                "use_worktree": False,
            }
        return {
            "status": "launched",
            "target_url": _build_prompt_target_url("", prompt),
            "sample_id": sample_id,
            "use_worktree": False,
        }

    if not use_worktree and sample_in_mode != "dev":
        return {
            "status": "launched",
            "target_url": _build_prompt_target_url("", prompt),
            "sample_id": sample_id,
            "use_worktree": False,
        }

    git_tag = sample.get("git_tag")
    worktree_path = _explore_worktree_path(sample_id) if use_worktree else _REPO_ROOT
    current_instance_target_url = _build_prompt_target_url("", prompt, str(worktree_path) if use_worktree else None)
    base_ref = str(git_tag) if (checkout_tag and git_tag) else None
    snapshot = _managed_explore_dev_snapshot()
    same_managed_worktree = str(snapshot.get("worktree_path") or "") == str(worktree_path)
    needs_prod_dev_monitor_step = runtime_mode == "production" and should_use_dev_instance

    if use_worktree and worktree_path.exists() and existing_worktree_action not in {"continue", "remove"}:
        return {
            "status": "needs_existing_worktree_action",
            "sample_id": sample_id,
            "worktree_path": str(worktree_path),
        }

    if _explore_tmux_session_exists() and not same_managed_worktree:
        _stop_managed_explore_dev_if_running()

    if same_managed_worktree and _explore_tmux_session_exists():
        if _probe_explore_dev_ready():
            return {
                "status": "monitor_dev_and_continue" if needs_prod_dev_monitor_step else "launched",
                "target_url": current_instance_target_url,
                "monitor_url": _explore_dev_base_url(),
                "sample_id": sample_id,
                "use_worktree": use_worktree,
                "worktree_path": str(worktree_path),
                "reused_running_dev": True,
            }
        if needs_prod_dev_monitor_step:
            existing_launch_id = str(snapshot.get("launch_id") or "").strip()
            if existing_launch_id and _get_explore_launch(existing_launch_id) is None:
                _store_explore_launch(
                    existing_launch_id,
                    _build_explore_launch_payload(
                        launch_id=existing_launch_id,
                        sample_id=sample_id,
                        use_worktree=use_worktree,
                        worktree_path=worktree_path,
                        target_url=current_instance_target_url,
                    ),
                )
            response: Dict[str, Any] = {
                "status": "monitor_dev_and_continue",
                "target_url": current_instance_target_url,
                "monitor_url": _explore_dev_base_url(),
                "sample_id": sample_id,
                "use_worktree": use_worktree,
                "worktree_path": str(worktree_path),
                "reused_running_dev": False,
            }
            if existing_launch_id:
                response["launch_id"] = existing_launch_id
            return response

    try:
        if use_worktree and existing_worktree_action == "remove" and same_managed_worktree and _explore_tmux_session_exists():
            _stop_managed_explore_dev_if_running()
        if use_worktree:
            result = _ensure_explore_worktree(
                worktree_path,
                sample_id=sample_id,
                existing_action=existing_worktree_action,
                base_ref=base_ref,
            )
            if result is not None:
                result.update({"sample_id": sample_id})
                return result

        try:
            _run_skillpilot_command(["stop", "--dev"], cwd=worktree_path, timeout=90.0)
        except Exception:
            pass

        _start_explore_dev_session(worktree_path)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(exc)})

    launch_id = uuid4().hex
    if needs_prod_dev_monitor_step:
        _store_explore_launch(
            launch_id,
            _build_explore_launch_payload(
                launch_id=launch_id,
                sample_id=sample_id,
                use_worktree=use_worktree,
                worktree_path=worktree_path,
                target_url=current_instance_target_url,
            ),
        )
        _set_managed_explore_dev(worktree_path=str(worktree_path), launch_id=launch_id, started_at=time.time())
        return {
            "status": "monitor_dev_and_continue",
            "launch_id": launch_id,
            "target_url": current_instance_target_url,
            "monitor_url": _explore_dev_base_url(),
            "sample_id": sample_id,
            "use_worktree": use_worktree,
            "worktree_path": str(worktree_path),
        }

    target_url = current_instance_target_url
    launch = _store_explore_launch(
        launch_id,
        _build_explore_launch_payload(
            launch_id=launch_id,
            sample_id=sample_id,
            use_worktree=use_worktree,
            worktree_path=worktree_path,
            target_url=target_url,
        ),
    )
    _set_managed_explore_dev(worktree_path=str(worktree_path), launch_id=launch_id, started_at=time.time())
    return launch


@router.get("/api/explore/template/status")
def explore_template_status(launch_id: str):
    launch = _get_explore_launch(launch_id)
    if not launch:
        return JSONResponse(status_code=404, content={"status": "error", "error": f"Unknown launch id: {launch_id}"})

    if launch.get("status") == "pending":
        if _probe_explore_dev_ready():
            updated = _update_explore_launch(launch_id, status="launched")
            if updated is not None:
                launch = updated
        elif not _explore_tmux_session_exists():
            created_at = float(launch.get("created_at") or 0.0)
            if time.time() - created_at < _EXPLORE_DEV_START_GRACE_SECONDS:
                return launch
            startup_log_path = str(launch.get("startup_log_path") or "").strip()
            error_message = "The managed dev session exited before the worktree WebUI became ready."
            if startup_log_path:
                error_message = f"{error_message} Check {startup_log_path} for startup logs."
            updated = _update_explore_launch(
                launch_id,
                status="error",
                error=error_message,
            )
            if updated is not None:
                launch = updated
                _clear_managed_explore_dev()

    return launch


@router.get("/api/tasks/tree")
def tasks_tree():
    if not TASKS_DIR.exists():
        return {"items": []}
    return {"items": build_tree(TASKS_DIR, TASKS_DIR)}


@router.get("/api/tasks/latest")
def tasks_latest():
    if not TASKS_DIR.exists():
        return {"path": None}
    latest = find_latest_course(TASKS_DIR, TASKS_DIR)
    if not latest:
        return {"path": None}
    return {"path": latest[0]}


@router.get("/api/tasks/content")
def task_content(path: str):
    try:
        file_path = _safe_tasks_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    raw = file_path.read_bytes()
    if not _is_text_bytes(raw):
        return JSONResponse(status_code=400, content={"error": "Binary files are not editable"})

    return {
        "path": path,
        "kind": _task_type_from_path(path),
        "content": raw.decode("utf-8", errors="replace"),
    }


@router.post("/api/tasks/save")
def task_save(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    workflow_path = str(payload.get("workflow_path") or "").strip()
    reference_files_raw = payload.get("reference_files")
    content = payload.get("content")
    check_workflow_resume = _bool_with_default(payload.get("check_workflow_resume"), False)
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing task path"})
    if not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "Invalid content"})
    reference_file_paths = [
        str(item).strip()
        for item in (reference_files_raw if isinstance(reference_files_raw, list) else [])
        if isinstance(item, str) and str(item).strip()
    ]

    try:
        file_path = _safe_tasks_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    file_path.write_text(content, encoding="utf-8")
    response: Dict[str, Any] = {"status": "ok"}
    if check_workflow_resume:
        if not workflow_path:
            return JSONResponse(status_code=400, content={"error": "workflow_path is required when checking workflow resume"})
        run_id, output_root = _task_workflow_output_dir(raw_path, workflow_path, reference_file_paths)
        response.update(
            {
                "workflow_resume_available": output_root.exists(),
                "workflow_run_id": run_id,
                "workflow_output_root": str(output_root),
            }
        )
    return response


@router.post("/api/tasks/create")
def task_create(payload: Dict[str, Any]):
    try:
        raw_folder, raw_file_name = _extract_task_create_parts(payload)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    has_requirements_payload = "requirements" in payload
    requirements = str(payload.get("requirements") or "")

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    folder_name = _normalize_task_folder_name(raw_folder)
    file_name = _normalize_task_file_name(raw_file_name)
    creates_task_folder = has_requirements_payload and file_name == "requirements.md"
    if folder_name:
        preferred_dir = TASKS_DIR / folder_name
        if creates_task_folder:
            parent_dir = preferred_dir if not preferred_dir.exists() else _unique_task_dir_path(folder_name)
            parent_dir.mkdir(parents=False, exist_ok=False)
        elif preferred_dir.exists() and preferred_dir.is_dir():
            parent_dir = preferred_dir
        else:
            parent_dir = preferred_dir if not preferred_dir.exists() else _unique_task_dir_path(folder_name)
            parent_dir.mkdir(parents=False, exist_ok=False)
    else:
        parent_dir = TASKS_DIR
        parent_dir.mkdir(parents=True, exist_ok=True)

    file_path = _unique_task_file_path(parent_dir, file_name)
    initial_content = requirements if has_requirements_payload else "# New Task\n\n"
    file_path.write_text(initial_content, encoding="utf-8")
    return {"status": "ok", "path": str(file_path.relative_to(TASKS_DIR))}


@router.post("/api/tasks/delete")
def task_delete(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    confirm_text = str(payload.get("confirm_text") or "").strip().lower()
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing task path"})

    try:
        file_path = _safe_tasks_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    parent_dir = file_path.parent
    if file_path.name == "requirements.md":
        if confirm_text != "delete":
            return JSONResponse(status_code=400, content={"error": "Type 'delete' to confirm removing the task"})
        if parent_dir == TASKS_DIR or TASKS_DIR not in parent_dir.parents:
            return JSONResponse(status_code=400, content={"error": "Invalid task directory"})
        shutil.rmtree(parent_dir)
        return {"status": "ok", "deleted": raw_path, "removedFolder": str(parent_dir.relative_to(TASKS_DIR))}

    file_path.unlink()
    removed_folder = None
    if parent_dir != TASKS_DIR:
        try:
            parent_dir.rmdir()
            removed_folder = str(parent_dir.relative_to(TASKS_DIR))
        except OSError:
            pass

    return {"status": "ok", "deleted": raw_path, "removedFolder": removed_folder}


@router.get("/api/tasks/file")
def task_file(path: str):
    try:
        file_path = _safe_tasks_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


@router.get("/api/media/tree")
def media_tree():
    if not MEDIA_DIR.exists():
        return {"items": []}
    return {"items": build_tree(MEDIA_DIR, MEDIA_DIR)}


@router.get("/api/media/latest")
def media_latest():
    if not MEDIA_DIR.exists():
        return {"path": None}
    latest = find_latest_course(MEDIA_DIR, MEDIA_DIR)
    if not latest:
        return {"path": None}
    return {"path": latest[0]}


@router.get("/api/media/content")
def media_content(path: str):
    try:
        file_path = _safe_media_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    raw = file_path.read_bytes()
    if not _is_text_bytes(raw):
        return JSONResponse(status_code=400, content={"error": "Binary files are not editable"})

    return {
        "path": path,
        "kind": _task_type_from_path(path),
        "content": raw.decode("utf-8", errors="replace"),
    }


@router.post("/api/media/save")
def media_save(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    content = payload.get("content")
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing media path"})
    if not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "Invalid content"})

    try:
        file_path = _safe_media_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    file_path.write_text(content, encoding="utf-8")
    return {"status": "ok"}


@router.post("/api/media/create")
def media_create(payload: Dict[str, Any]):
    try:
        raw_folder, raw_file_name = _extract_task_create_parts(payload)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    requirements = str(payload.get("requirements") or "")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    folder_name = _normalize_task_folder_name(raw_folder)
    file_name = _normalize_task_file_name(raw_file_name)
    if folder_name:
        preferred_dir = MEDIA_DIR / folder_name
        parent_dir = preferred_dir if not preferred_dir.exists() else _unique_media_dir_path(folder_name)
        parent_dir.mkdir(parents=False, exist_ok=False)
    else:
        parent_dir = MEDIA_DIR
        parent_dir.mkdir(parents=True, exist_ok=True)

    file_path = _unique_task_file_path(parent_dir, file_name)
    file_path.write_text(requirements, encoding="utf-8")
    return {"status": "ok", "path": str(file_path.relative_to(MEDIA_DIR))}


@router.post("/api/media/delete")
def media_delete(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    confirm_text = str(payload.get("confirm_text") or "").strip().lower()
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing media path"})

    try:
        file_path = _safe_media_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    parent_dir = file_path.parent
    if file_path.name == "requirements.md":
        if confirm_text != "delete":
            return JSONResponse(status_code=400, content={"error": "Type 'delete' to confirm removing the media"})
        if parent_dir == MEDIA_DIR or MEDIA_DIR not in parent_dir.parents:
            return JSONResponse(status_code=400, content={"error": "Invalid media directory"})
        shutil.rmtree(parent_dir)
        return {"status": "ok", "deleted": raw_path, "removedFolder": str(parent_dir.relative_to(MEDIA_DIR))}

    file_path.unlink()
    removed_folder = None
    if parent_dir != MEDIA_DIR:
        try:
            parent_dir.rmdir()
            removed_folder = str(parent_dir.relative_to(MEDIA_DIR))
        except OSError:
            pass

    return {"status": "ok", "deleted": raw_path, "removedFolder": removed_folder}


@router.get("/api/media/file")
def media_file(path: str):
    try:
        file_path = _safe_media_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


@router.get("/api/vibe-coding/tree")
def vibe_coding_tree():
    if not VIBE_CODING_DIR.exists():
        return {"items": []}
    return {"items": build_tree(VIBE_CODING_DIR, VIBE_CODING_DIR)}


@router.get("/api/vibe-coding/projects")
def vibe_coding_projects():
    if not VIBE_CODING_DIR.exists():
        return {"items": []}
    items = [
        summary
        for summary in (_vibe_project_summary(path) for path in VIBE_CODING_DIR.iterdir())
        if summary is not None
    ]
    items.sort(key=lambda item: (-float(item.get("mtime") or 0), str(item.get("display_name") or "")))
    return {"items": items}


@router.get("/api/vibe-coding/latest")
def vibe_coding_latest():
    if not VIBE_CODING_DIR.exists():
        return {"path": None}
    latest = find_latest_course(VIBE_CODING_DIR, VIBE_CODING_DIR)
    if not latest:
        return {"path": None}
    return {"path": latest[0]}


@router.get("/api/vibe-coding/content")
def vibe_coding_content(path: str):
    try:
        file_path = _safe_vibe_coding_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    raw = file_path.read_bytes()
    if not _is_text_bytes(raw):
        return JSONResponse(status_code=400, content={"error": "Binary files are not editable"})

    return {
        "path": path,
        "kind": _task_type_from_path(path),
        "content": raw.decode("utf-8", errors="replace"),
    }


@router.post("/api/vibe-coding/save")
def vibe_coding_save(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    content = payload.get("content")
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing vibe coding path"})
    if not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "Invalid content"})

    try:
        file_path = _safe_vibe_coding_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    file_path.write_text(content, encoding="utf-8")
    return {"status": "ok"}


@router.post("/api/vibe-coding/create-project")
def vibe_coding_create_project(payload: Dict[str, Any]):
    project_name = str(payload.get("project_name") or "").strip()
    requirements = str(payload.get("requirements") or "")
    if not project_name:
        return JSONResponse(status_code=400, content={"error": "Project name is required"})

    VIBE_CODING_DIR.mkdir(parents=True, exist_ok=True)
    normalized_project = _normalize_vibe_project_name(project_name)
    project_dir = _unique_vibe_project_dir_path(normalized_project)
    project_dir.mkdir(parents=False, exist_ok=False)
    design_docs_dir = project_dir / VIBE_CODING_DESIGN_DOCS_DIR
    design_docs_dir.mkdir(parents=True, exist_ok=True)
    (design_docs_dir / VIBE_CODING_ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)
    file_path = design_docs_dir / "requirements.md"
    file_path.write_text(requirements, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(file_path.relative_to(VIBE_CODING_DIR)),
        "project": project_dir.name,
    }


@router.post("/api/vibe-coding/create-update-request")
def vibe_coding_create_update_request(payload: Dict[str, Any]):
    project_name = str(payload.get("project_name") or "").strip()
    content = str(payload.get("content") or "")
    try:
        _, file_path, normalized_project = _ensure_vibe_project_file(project_name, "update.md")
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    file_path.write_text(content, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(file_path.relative_to(VIBE_CODING_DIR)),
        "project": normalized_project,
    }


@router.post("/api/vibe-coding/create-issue-report")
def vibe_coding_create_issue_report(payload: Dict[str, Any]):
    project_name = str(payload.get("project_name") or "").strip()
    content = str(payload.get("content") or "")
    try:
        _, file_path, normalized_project = _ensure_vibe_project_file(project_name, "issues.md")
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    file_path.write_text(content, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(file_path.relative_to(VIBE_CODING_DIR)),
        "project": normalized_project,
    }


@router.post("/api/vibe-coding/delete")
def vibe_coding_delete(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    confirm_text = str(payload.get("confirm_text") or "").strip().lower()
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing vibe coding path"})

    try:
        file_path = _safe_vibe_coding_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    project_dir = _vibe_project_root_for_file(file_path)
    if _is_vibe_project_requirements_file(file_path):
        if confirm_text != "delete":
            return JSONResponse(status_code=400, content={"error": "Type 'delete' to confirm removing the project"})
        try:
            _remove_project_dir(project_dir)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        return {
            "status": "ok",
            "deleted": raw_path,
            "removedFolder": str(project_dir.relative_to(VIBE_CODING_DIR)),
        }

    file_path.unlink()
    removed_folder = None
    parent_dir = file_path.parent
    design_docs_dir = project_dir / VIBE_CODING_DESIGN_DOCS_DIR
    cleanup_dir = project_dir if parent_dir == project_dir else parent_dir
    if cleanup_dir != design_docs_dir:
        try:
            cleanup_dir.rmdir()
            removed_folder = str(cleanup_dir.relative_to(VIBE_CODING_DIR))
        except OSError:
            pass

    return {"status": "ok", "deleted": raw_path, "removedFolder": removed_folder}


@router.get("/api/vibe-coding/file")
def vibe_coding_file(path: str):
    try:
        file_path = _safe_vibe_coding_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


@router.get("/api/research/tree")
def research_tree():
    if not RESEARCH_DIR.exists():
        return {"items": []}
    return {"items": build_tree(RESEARCH_DIR, RESEARCH_DIR)}


@router.get("/api/research/latest")
def research_latest():
    if not RESEARCH_DIR.exists():
        return {"path": None}
    latest = find_latest_course(RESEARCH_DIR, RESEARCH_DIR)
    if not latest:
        return {"path": None}
    return {"path": latest[0]}


@router.get("/api/research/content")
def research_content(path: str):
    try:
        file_path = _safe_research_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    raw = file_path.read_bytes()
    if not _is_text_bytes(raw):
        return JSONResponse(status_code=400, content={"error": "Binary files are not editable"})

    return {
        "path": path,
        "kind": _task_type_from_path(path),
        "content": raw.decode("utf-8", errors="replace"),
    }


@router.post("/api/research/save")
def research_save(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    content = payload.get("content")
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing research path"})
    if not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "Invalid content"})

    try:
        file_path = _safe_research_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    file_path.write_text(content, encoding="utf-8")
    return {"status": "ok"}


@router.post("/api/research/create-topic")
def research_create_topic(payload: Dict[str, Any]):
    topic_name = str(payload.get("topic_name") or "").strip()
    requirements = str(payload.get("requirements") or "")
    if not topic_name:
        return JSONResponse(status_code=400, content={"error": "Topic name is required"})

    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    normalized_topic = _normalize_research_topic_name(topic_name)
    topic_dir = _unique_research_topic_dir_path(normalized_topic)
    topic_dir.mkdir(parents=False, exist_ok=False)
    file_path = topic_dir / "requirements.md"
    file_path.write_text(requirements, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(file_path.relative_to(RESEARCH_DIR)),
        "topic": topic_dir.name,
    }


@router.post("/api/research/delete")
def research_delete(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    confirm_text = str(payload.get("confirm_text") or "").strip().lower()
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing research path"})

    try:
        file_path = _safe_research_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    parent_dir = file_path.parent
    if file_path.name == "requirements.md":
        if confirm_text != "delete":
            return JSONResponse(status_code=400, content={"error": "Type 'delete' to confirm removing the topic"})
        if parent_dir == RESEARCH_DIR or RESEARCH_DIR not in parent_dir.parents:
            return JSONResponse(status_code=400, content={"error": "Invalid topic directory"})
        shutil.rmtree(parent_dir)
        return {"status": "ok", "deleted": raw_path, "removedFolder": str(parent_dir.relative_to(RESEARCH_DIR))}

    file_path.unlink()
    removed_folder = None
    if parent_dir != RESEARCH_DIR:
        try:
            parent_dir.rmdir()
            removed_folder = str(parent_dir.relative_to(RESEARCH_DIR))
        except OSError:
            pass

    return {"status": "ok", "deleted": raw_path, "removedFolder": removed_folder}


@router.get("/api/research/file")
def research_file(path: str):
    try:
        file_path = _safe_research_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


@router.get("/api/skill-pilot-development/features")
def skill_pilot_development_features():
    return {"items": _skill_pilot_feature_catalog()}


@router.get("/api/skill-pilot-development/tree")
def skill_pilot_development_tree():
    if not SKILL_PILOT_DEVELOPMENT_DIR.exists():
        return {"items": []}
    return {"items": build_tree(SKILL_PILOT_DEVELOPMENT_DIR, SKILL_PILOT_DEVELOPMENT_DIR)}


@router.get("/api/skill-pilot-development/latest")
def skill_pilot_development_latest():
    if not SKILL_PILOT_DEVELOPMENT_DIR.exists():
        return {"path": None}
    latest = find_latest_course(SKILL_PILOT_DEVELOPMENT_DIR, SKILL_PILOT_DEVELOPMENT_DIR)
    if not latest:
        return {"path": None}
    return {"path": latest[0]}


@router.get("/api/skill-pilot-development/content")
def skill_pilot_development_content(path: str):
    try:
        file_path = _safe_skill_pilot_development_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    raw = file_path.read_bytes()
    if not _is_text_bytes(raw):
        return JSONResponse(status_code=400, content={"error": "Binary files are not editable"})

    return {
        "path": path,
        "kind": _task_type_from_path(path),
        "content": raw.decode("utf-8", errors="replace"),
    }


@router.post("/api/skill-pilot-development/save")
def skill_pilot_development_save(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    content = payload.get("content")
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing development path"})
    if not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "Invalid content"})

    try:
        file_path = _safe_skill_pilot_development_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    file_path.write_text(content, encoding="utf-8")
    return {"status": "ok"}


@router.post("/api/skill-pilot-development/create-feature")
def skill_pilot_development_create_feature(payload: Dict[str, Any]):
    feature_name = str(payload.get("feature_name") or "").strip()
    content = str(payload.get("content") or "")
    related_features = payload.get("related_features")
    if not feature_name:
        return JSONResponse(status_code=400, content={"error": "Feature name is required"})

    normalized_feature = _normalize_skill_pilot_feature_name(feature_name)
    SKILL_PILOT_DEVELOPMENT_DIR.mkdir(parents=True, exist_ok=True)
    feature_dir = _unique_skill_pilot_feature_dir_path(normalized_feature)
    feature_dir.mkdir(parents=False, exist_ok=False)
    file_path = feature_dir / "requirements.md"
    file_path.write_text(
        _append_related_feature_references(
            content,
            [str(item) for item in (related_features if isinstance(related_features, list) else []) if str(item).strip()],
        ),
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "path": str(file_path.relative_to(SKILL_PILOT_DEVELOPMENT_DIR)),
        "feature": feature_dir.name,
    }


@router.post("/api/skill-pilot-development/create-update-request")
def skill_pilot_development_create_update_request(payload: Dict[str, Any]):
    feature_name = str(payload.get("feature_name") or "").strip()
    content = str(payload.get("content") or "")
    related_features = payload.get("related_features")
    if not feature_name:
        return JSONResponse(status_code=400, content={"error": "Feature name is required"})

    normalized_feature = _normalize_skill_pilot_feature_name(feature_name)
    feature_dir = SKILL_PILOT_DEVELOPMENT_DIR / normalized_feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    file_path = feature_dir / "update.md"
    file_path.write_text(
        _append_related_feature_references(
            content,
            [str(item) for item in (related_features if isinstance(related_features, list) else []) if str(item).strip()],
        ),
        encoding="utf-8",
    )
    return {"status": "ok", "path": str(file_path.relative_to(SKILL_PILOT_DEVELOPMENT_DIR)), "feature": normalized_feature}


@router.post("/api/skill-pilot-development/create-issue-report")
def skill_pilot_development_create_issue_report(payload: Dict[str, Any]):
    feature_name = str(payload.get("feature_name") or "").strip()
    content = str(payload.get("content") or "")
    related_features = payload.get("related_features")
    if not feature_name:
        return JSONResponse(status_code=400, content={"error": "Feature name is required"})

    normalized_feature = _normalize_skill_pilot_feature_name(feature_name)
    feature_dir = SKILL_PILOT_DEVELOPMENT_DIR / normalized_feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    file_path = feature_dir / "issues.md"
    file_path.write_text(
        _append_related_feature_references(
            content,
            [str(item) for item in (related_features if isinstance(related_features, list) else []) if str(item).strip()],
        ),
        encoding="utf-8",
    )
    return {"status": "ok", "path": str(file_path.relative_to(SKILL_PILOT_DEVELOPMENT_DIR)), "feature": normalized_feature}


@router.post("/api/skill-pilot-development/delete")
def skill_pilot_development_delete(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    confirm_text = str(payload.get("confirm_text") or "").strip().lower()
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing development path"})

    try:
        file_path = _safe_skill_pilot_development_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    feature_dir = file_path.parent
    if file_path.name == "requirements.md":
        if confirm_text != "delete":
            return JSONResponse(status_code=400, content={"error": "Type 'delete' to confirm removing the feature"})
        if feature_dir == SKILL_PILOT_DEVELOPMENT_DIR or SKILL_PILOT_DEVELOPMENT_DIR not in feature_dir.parents:
            return JSONResponse(status_code=400, content={"error": "Invalid feature directory"})
        shutil.rmtree(feature_dir)
        return {"status": "ok", "deleted": raw_path, "removedFolder": str(feature_dir.relative_to(SKILL_PILOT_DEVELOPMENT_DIR))}

    file_path.unlink()
    removed_folder = None
    if feature_dir != SKILL_PILOT_DEVELOPMENT_DIR:
        try:
            feature_dir.rmdir()
            removed_folder = str(feature_dir.relative_to(SKILL_PILOT_DEVELOPMENT_DIR))
        except OSError:
            pass

    return {"status": "ok", "deleted": raw_path, "removedFolder": removed_folder}


@router.get("/api/skill-pilot-development/file")
def skill_pilot_development_file(path: str):
    try:
        file_path = _safe_skill_pilot_development_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


@router.get("/api/courses/tree")
def courses_tree():
    if not COURSES_DIR.exists():
        return {"items": []}
    return {"items": build_tree(COURSES_DIR)}


@router.get("/api/courses/latest")
def courses_latest():
    if not COURSES_DIR.exists():
        return {"path": None}
    latest = find_latest_course(COURSES_DIR)
    if not latest:
        return {"path": None}
    return {"path": latest[0]}


@router.get("/api/courses/content")
def course_content(course: str):
    file_path = safe_course_path(course)
    content = file_path.read_text(encoding="utf-8", errors="replace")
    meta = read_course_meta(content)
    return {"path": course, "content": content, "meta": meta}


@router.post("/api/courses/reset")
def reset_course_progress(payload: Dict[str, Any]):
    course = payload.get("course")
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updated = write_course_meta(text, {"last_step": 0})
    file_path.write_text(updated, encoding="utf-8")
    return {"status": "ok"}


@router.post("/api/courses/save")
def save_course_content(payload: Dict[str, Any]):
    course = payload.get("course")
    content = payload.get("content")
    if course is None:
        return JSONResponse(status_code=400, content={"error": "Missing course path"})
    if not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "Invalid content"})
    file_path = safe_course_path(course)
    file_path.write_text(content, encoding="utf-8")
    return {"status": "ok"}


def _write_text_atomic(path: Path, text: str) -> None:
    temp_path = path.with_name(f".{path.name}.tmp-{uuid4().hex}")
    try:
        temp_path.write_text(text, encoding="utf-8")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_new_workflow_file_with_collision_retry(target_dir: Path, filename: str, content_text: str) -> Path:
    if not filename.endswith(".json"):
        filename = normalize_workflow_filename(filename)
    if not is_valid_workflow_filename(filename):
        raise ValueError("Invalid workflow filename")

    base = filename[:-5]
    candidate = filename
    index = 1
    while True:
        candidate_path = target_dir / candidate
        try:
            with candidate_path.open("x", encoding="utf-8") as fh:
                fh.write(content_text)
            return candidate_path
        except FileExistsError:
            candidate = f"{base}_{index}.json"
            index += 1


@router.get("/api/workflows/tree")
def workflows_tree():
    if not WORKFLOWS_DIR.exists():
        return {"items": []}
    return {"items": build_workflow_tree(WORKFLOWS_DIR, WORKFLOWS_DIR)}


@router.get("/api/workflows/latest")
def workflows_latest():
    if not WORKFLOWS_DIR.exists():
        return {"path": None}
    latest = find_latest_workflow(WORKFLOWS_DIR)
    return {"path": latest}


@router.get("/api/workflows/content")
def workflows_content(workflow: str):
    file_path = safe_workflow_path(WORKFLOWS_DIR, workflow)
    try:
        content = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid workflow JSON"})
    if not isinstance(content, dict):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid workflow document",
                "errors": [
                    {
                        "rule": "SHAPE_WORKFLOW",
                        "message": "`workflow` must be an object.",
                        "node_ids": [],
                        "edge_ids": [],
                    }
                ],
            },
        )
    errors = validate_workflow_doc(content)
    if errors:
        return JSONResponse(status_code=400, content={"error": "Invalid workflow document", "errors": errors})
    return {"path": workflow, "content": content}


@router.get("/api/workflows/execute/status")
def workflows_execute_status():
    return _workflow_execute_status()


@router.post("/api/workflows/execute")
def workflows_execute(payload: Dict[str, Any]):
    workflow = str(payload.get("workflow") or "").strip()
    workflow_prompt = str(payload.get("prompt") or "").strip()
    native_terminal = _bool_with_default(payload.get("native_terminal"), False)
    resume = _bool_with_default(payload.get("resume"), False)
    sandbox = payload.get("sandbox")
    auto = payload.get("auto")
    network = payload.get("network")
    next_node_trigger = str(payload.get("next_node_trigger") or "auto_continue").strip().lower()
    requested_start_path = payload.get("path")

    if not workflow:
        return JSONResponse(status_code=400, content={"error": "workflow is required"})
    if not workflow_prompt:
        return JSONResponse(status_code=400, content={"error": "prompt is required"})
    if next_node_trigger not in {"auto_continue", "start_by_prompt"}:
        return JSONResponse(status_code=400, content={"error": "next_node_trigger must be auto_continue or start_by_prompt"})
    if workflow.startswith("core/workflows/"):
        workflow = workflow[len("core/workflows/") :]

    try:
        workflow_file = safe_workflow_path(WORKFLOWS_DIR, workflow)
    except Exception as exc:  # noqa: BLE001
        detail = getattr(exc, "detail", str(exc))
        status_code = int(getattr(exc, "status_code", 400))
        return JSONResponse(status_code=status_code, content={"error": str(detail)})
    try:
        start_dir = _resolve_terminal_start_dir(requested_start_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    _stop_existing_workflow_execute_thread()

    try:
        session_name = _create_named_tmux_session(WORKFLOW_EXECUTE_SESSION_NAME, start_dir=start_dir)
        attach_command = _build_tmux_attach_command_any(session_name)
        native_status = _open_native_terminal_for_tmux(session_name) if native_terminal else {"requested": False, "opened": False}
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    if native_terminal and "requested" not in native_status:
        native_status["requested"] = True

    logger.info(
        "[workflow-execute] request workflow=%s session=%s native_terminal=%s sandbox=%s auto=%s network=%s next_node_trigger=%s",
        workflow,
        session_name,
        native_terminal,
        sandbox,
        auto,
        network,
        next_node_trigger,
    )
    start_result = _start_workflow_execute_thread(
        workflow_file=workflow_file,
        workflow_prompt=workflow_prompt,
        session_name=session_name,
        resume=resume,
        sandbox=sandbox,
        auto=auto,
        network=network,
        next_node_trigger=next_node_trigger,
        session_managed=True,
    )

    return {
        "session": {
            "name": session_name,
            "attach_command": attach_command,
            "cwd": str(start_dir),
        },
        "workflow_thread": start_result["workflow_thread"],
        "native_terminal": native_status,
    }


def start_workflow_execute_in_session(
    *,
    workflow: str,
    workflow_prompt: str,
    session_name: str,
    resume: bool = False,
    sandbox: Any = None,
    auto: Any = None,
    network: Any = None,
    next_node_trigger: str = "start_by_prompt",
) -> Dict[str, Any]:
    workflow_name = str(workflow or "").strip()
    prompt_text = str(workflow_prompt or "").strip()
    requested_session = str(session_name or "").strip()
    trigger = str(next_node_trigger or "start_by_prompt").strip().lower()

    if not workflow_name:
        raise ValueError("workflow is required")
    if not prompt_text:
        raise ValueError("prompt is required")
    if not requested_session:
        raise ValueError("tmux session name is required")
    if trigger not in {"auto_continue", "start_by_prompt"}:
        raise ValueError("next_node_trigger must be auto_continue or start_by_prompt")

    if workflow_name.startswith("core/workflows/"):
        workflow_name = workflow_name[len("core/workflows/") :]

    workflow_file = safe_workflow_path(WORKFLOWS_DIR, workflow_name)
    safe_session = _validate_tmux_session_name_any(requested_session)
    if not _tmux_session_exists(safe_session):
        raise RuntimeError(f"tmux session not found: {safe_session}")

    _stop_existing_workflow_execute_thread()
    logger.info(
        "[workflow-execute] external-session request workflow=%s session=%s resume=%s sandbox=%s auto=%s network=%s next_node_trigger=%s",
        workflow_name,
        safe_session,
        resume,
        sandbox,
        auto,
        network,
        trigger,
    )
    return _start_workflow_execute_thread(
        workflow_file=workflow_file,
        workflow_prompt=prompt_text,
        session_name=safe_session,
        resume=resume,
        sandbox=sandbox,
        auto=auto,
        network=network,
        next_node_trigger=trigger,
        session_managed=False,
        external_first_node=True,
    )


@router.post("/api/workflows/execute/continue")
def workflows_execute_continue():
    return request_workflow_continue_signal(source="api")


@router.post("/api/workflows/validate")
def workflows_validate(payload: Dict[str, Any]):
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        return JSONResponse(status_code=400, content={"valid": False, "errors": [{"rule": "SHAPE_WORKFLOW", "message": "`workflow` must be an object.", "node_ids": [], "edge_ids": []}]})
    errors = validate_workflow_doc(workflow)
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/api/workflows/save")
def workflows_save(payload: Dict[str, Any]):
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        return JSONResponse(status_code=400, content={"status": "error", "valid": False, "errors": [{"rule": "SHAPE_WORKFLOW", "message": "`workflow` must be an object.", "node_ids": [], "edge_ids": []}]})

    errors = validate_workflow_doc(workflow)
    if errors:
        return JSONResponse(status_code=400, content={"status": "error", "valid": False, "errors": errors})

    existing_path_raw = str(payload.get("path") or "").strip()
    existing_file: Path | None = None
    if existing_path_raw:
        existing_file = safe_workflow_path(WORKFLOWS_DIR, existing_path_raw)

    operation = str(payload.get("operation") or "save").strip().lower()
    if operation not in {"save", "duplicate"}:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "valid": False,
                "errors": [{"rule": "OPERATION", "message": "Invalid workflow save operation.", "node_ids": [], "edge_ids": []}],
            },
        )

    raw_filename = str(payload.get("filename") or "").strip()
    if existing_file is not None and not raw_filename:
        filename = existing_file.name
    elif raw_filename:
        if not raw_filename.endswith(".json"):
            raw_filename = f"{raw_filename}.json"
        if not is_valid_workflow_filename(raw_filename):
            normalized = normalize_workflow_filename(raw_filename[:-5] if raw_filename.endswith(".json") else raw_filename)
            filename = normalized
        else:
            filename = raw_filename
    else:
        filename = normalize_workflow_filename(str(workflow.get("name") or "workflow"))

    target_dir = existing_file.parent if existing_file is not None else WORKFLOWS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    desired_path = target_dir / filename
    to_save = dict(workflow)
    to_save["version"] = str(to_save.get("version") or "1.0")
    to_save["updated_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    payload_text = json.dumps(to_save, indent=2) + "\n"

    if operation == "duplicate":
        try:
            final_path = _write_new_workflow_file_with_collision_retry(target_dir, filename, payload_text)
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "valid": False,
                    "errors": [{"rule": "FILENAME", "message": str(exc), "node_ids": [], "edge_ids": []}],
                },
            )
    elif existing_file is not None and desired_path.resolve() == existing_file.resolve():
        final_path = existing_file
        _write_text_atomic(final_path, payload_text)
    else:
        if desired_path.exists():
            return JSONResponse(
                status_code=409,
                content={
                    "status": "error",
                    "valid": False,
                    "errors": [{"rule": "FILENAME_EXISTS", "message": "Workflow filename already exists.", "node_ids": [], "edge_ids": []}],
                },
            )
        try:
            _write_text_atomic(desired_path, payload_text)
            final_path = desired_path
            if existing_file is not None and existing_file.exists():
                existing_file.unlink()
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "valid": False,
                    "errors": [{"rule": "FILENAME", "message": str(exc), "node_ids": [], "edge_ids": []}],
                },
            )

    saved_rel_path = str(final_path.relative_to(WORKFLOWS_DIR))
    return {"status": "ok", "path": saved_rel_path, "saved_name": final_path.name}


@router.post("/api/workflows/delete")
def workflows_delete(payload: Dict[str, Any]):
    workflow = str(payload.get("path") or "").strip()
    if not workflow:
        return JSONResponse(status_code=400, content={"error": "Missing workflow path"})

    file_path = safe_workflow_path(WORKFLOWS_DIR, workflow)
    file_path.unlink()
    return {"status": "ok"}
