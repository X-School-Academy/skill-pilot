from routes_shared import *

import routes as routes_root


# Fix #5: 10 MB read limit to prevent OOM on large files
_FILE_READ_MAX_BYTES = 10 * 1024 * 1024

# Fix #9: directory names that produce useless/enormous listings
_LISTING_SKIP = frozenset({".git", "node_modules", "__pycache__", ".DS_Store"})

_PROTECTED_FILE_CONTENT_PATHS = frozenset({"config/.env"})
_FILE_WATCH_SKIP = frozenset({".git", "node_modules", "__pycache__", ".next"})
_FILE_MANAGER_PROJECT_ROOT_ID = "/$project"
_FILE_MANAGER_WORKTREE_PREFIX = "/$worktree"


def _repo_root() -> Path:
    return getattr(routes_root, "_REPO_ROOT", _REPO_ROOT)


def _repo_root_resolved() -> Path:
    current = getattr(routes_root, "_REPO_ROOT_RESOLVED", None)
    if isinstance(current, Path):
        return current
    return _repo_root().resolve()


def _file_manager_supports_worktrees() -> bool:
    return (_repo_root_resolved() / ".git").is_dir()


def _read_gitdir_pointer(path: Path) -> Path | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (path.parent / candidate).resolve()
        else:
            candidate = candidate.resolve()
    except OSError:
        return None
    return candidate


def _discover_git_worktrees() -> list[dict[str, Any]]:
    if not _file_manager_supports_worktrees():
        return []

    worktrees: list[dict[str, Any]] = []
    worktrees_dir = _repo_root_resolved() / ".git" / "worktrees"
    if not worktrees_dir.is_dir():
        return worktrees

    for entry in sorted(worktrees_dir.iterdir(), key=lambda item: item.name.lower()):
        gitdir_pointer = entry / "gitdir"
        if not gitdir_pointer.is_file():
            continue
        gitdir_path = _read_gitdir_pointer(gitdir_pointer)
        if not gitdir_path:
            continue
        worktree_path = gitdir_path.parent.resolve()
        if not worktree_path.is_dir() or worktree_path == _repo_root_resolved():
            continue
        worktrees.append(
            {
                "id": f"{_FILE_MANAGER_WORKTREE_PREFIX}/{entry.name}",
                "label": worktree_path.name,
                "path": worktree_path,
                "kind": "worktree",
            }
        )
    return worktrees


def _file_manager_multi_root_enabled() -> bool:
    return _file_manager_supports_worktrees() and len(_discover_git_worktrees()) > 0


def _discover_file_manager_roots() -> list[dict[str, Any]]:
    worktrees = _discover_git_worktrees()
    project_root = {
        "id": _FILE_MANAGER_PROJECT_ROOT_ID if worktrees else "/",
        "label": _repo_root_resolved().name,
        "path": _repo_root_resolved(),
        "kind": "project",
    }
    if not worktrees:
        return [project_root]
    return [project_root, *worktrees]


def _file_manager_roots_by_id() -> dict[str, dict[str, Any]]:
    return {str(root["id"]): root for root in _discover_file_manager_roots()}


def _file_watch_roots() -> list[Path]:
    return [Path(root["path"]) for root in _discover_file_manager_roots()]


def _path_is_within_root(path: Path, root_path: Path) -> bool:
    return path == root_path or root_path in path.parents


def _root_relative_path(root_id: str, relative: str) -> str:
    if not relative or relative == ".":
        return root_id
    return f"/{relative}" if root_id == "/" else f"{root_id}/{relative}"


def _file_manager_root_for_absolute_path(path: Path) -> dict[str, Any] | None:
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return None
    roots = sorted(
        _discover_file_manager_roots(),
        key=lambda root: len(Path(root["path"]).parts),
        reverse=True,
    )
    for root in roots:
        root_path = Path(root["path"])
        if _path_is_within_root(resolved, root_path):
            return root
    return None


def _relative_path_within_file_root(path: Path) -> str | None:
    root = _file_manager_root_for_absolute_path(path)
    if root is None:
        return None
    try:
        return path.resolve(strict=False).relative_to(Path(root["path"])).as_posix()
    except (OSError, ValueError):
        return None


def _normalize_files_repo_path(path: Path) -> str | None:
    try:
        resolved = path.resolve(strict=False)
        lexical = path.absolute()
    except OSError:
        return None
    roots = sorted(
        _discover_file_manager_roots(),
        key=lambda root: len(Path(root["path"]).parts),
        reverse=True,
    )
    for root in roots:
        root_path = Path(root["path"])
        if not _path_is_within_root(lexical, root_path):
            continue
        if not _path_is_within_root(resolved, root_path):
            continue
        try:
            relative = lexical.relative_to(root_path).as_posix()
        except ValueError:
            continue
        return _root_relative_path(str(root["id"]), relative)
    return None


_FILE_REALTIME_HUB = FileRealtimeHub(
    _file_watch_roots,
    skip_dir_names=_FILE_WATCH_SKIP,
    normalize_path=_normalize_files_repo_path,
)


def _is_virtual_file_root(path: str) -> bool:
    normalized = "/" if path == "/" else path.rstrip("/")
    return normalized in _file_manager_roots_by_id()


def _safe_files_path(raw: str) -> Path:
    """Resolve a user-supplied path against the project root, blocking traversal."""
    if not raw:
        raise ValueError("Missing path")
    normalized = "/" if raw == "/" else f"/{raw.lstrip('/')}".rstrip("/")
    roots = _file_manager_roots_by_id()

    if normalized == "/" and _file_manager_multi_root_enabled():
        raise ValueError("Path outside project root")

    for root_id, root in roots.items():
        if normalized != root_id and not normalized.startswith(f"{root_id}/"):
            continue
        suffix = normalized[len(root_id):].lstrip("/")
        base_path = Path(root["path"])
        if not suffix:
            return base_path
        candidate = (base_path / suffix).resolve()
        if not _path_is_within_root(candidate, base_path):
            raise ValueError("Path outside project root")
        return candidate

    rel = normalized.lstrip("/").replace("\\", "/")
    if not rel:
        return _repo_root_resolved()
    candidate = (_repo_root() / rel).resolve()
    repo_root_resolved = _repo_root_resolved()
    if candidate != repo_root_resolved and repo_root_resolved not in candidate.parents:
        raise ValueError("Path outside project root")
    return candidate


def _content_access_path(raw: str) -> Path:
    candidate = _safe_files_path(raw)
    relative = _relative_path_within_file_root(candidate)
    if relative is None:
        raise ValueError("Path outside project root")
    if relative in _PROTECTED_FILE_CONTENT_PATHS:
        raise PermissionError("Permission denied")
    return candidate


def _file_entity(path: Path) -> dict:
    stat = path.stat()
    rel = _normalize_files_repo_path(path)
    if rel is None:
        raise ValueError("Path outside project root")
    entry: dict = {
        "id": rel,
        "type": "folder" if path.is_dir() else "file",
        "size": stat.st_size,
        "date": int(stat.st_mtime * 1000),
    }
    if path.is_dir():
        entry["lazy"] = True
    return entry


def _virtual_root_entry(root: dict[str, Any]) -> dict[str, Any]:
    stat = Path(root["path"]).stat()
    return {
        "id": str(root["id"]),
        "type": "folder",
        "size": stat.st_size,
        "date": int(stat.st_mtime * 1000),
        "lazy": True,
        "label": str(root["label"]),
        "rootKind": str(root["kind"]),
        "virtualRoot": True,
    }


@router.get("/api/files/info")
def files_info():
    roots = _discover_file_manager_roots()
    return {
        "root": str(_repo_root()),
        "id": "/",
        "projectName": _repo_root_resolved().name,
        "supportsWorktrees": _file_manager_multi_root_enabled(),
        "roots": [
            {
                "id": str(root["id"]),
                "label": str(root["label"]),
                "kind": str(root["kind"]),
            }
            for root in roots
        ],
    }


@router.get("/api/files/list")
def files_list(path: str = "/"):
    if path == "/" and _file_manager_multi_root_enabled():
        roots = _discover_file_manager_roots()
        return {
            "id": path,
            "data": [_virtual_root_entry(root) for root in roots],
        }
    try:
        dir_path = _safe_files_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    if not dir_path.exists():
        return JSONResponse(status_code=404, content={"error": "Path not found"})
    if not dir_path.is_dir():
        return JSONResponse(status_code=400, content={"error": "Not a directory"})
    items = []
    try:
        for child in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if child.name in _LISTING_SKIP:
                continue
            try:
                items.append(_file_entity(child))
            except (PermissionError, OSError, ValueError):
                # Fix #8: ValueError from relative_to when symlink resolves outside root
                pass
    except PermissionError:
        return JSONResponse(status_code=403, content={"error": "Permission denied"})
    return {"id": path, "data": items}


@router.get("/api/files/read")
def files_read(path: str):
    try:
        file_path = _content_access_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    if not file_path.exists() or not file_path.is_file():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    # Fix #5: reject files larger than the read limit to avoid OOM
    file_size = file_path.stat().st_size
    if file_size > _FILE_READ_MAX_BYTES:
        mb = file_size // (1024 * 1024)
        return JSONResponse(
            status_code=413,
            content={"error": f"File too large to edit ({mb} MB > 10 MB limit)"},
        )
    try:
        raw = file_path.read_bytes()
    except PermissionError:
        return JSONResponse(status_code=403, content={"error": "Permission denied"})
    if not _is_text_bytes(raw):
        return JSONResponse(status_code=415, content={"error": "Binary file cannot be read as text"})
    return {
        "path": path,
        "content": raw.decode("utf-8", errors="replace"),
        "kind": _task_type_from_path(path),
    }


@router.post("/api/files/write")
async def files_write(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    raw_path = str(payload.get("path") or "").strip()
    content = payload.get("content")
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Missing path"})
    if not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "Invalid content"})
    try:
        file_path = _content_access_path(raw_path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        file_path.write_text(content, encoding="utf-8")
    except PermissionError:
        return JSONResponse(status_code=403, content={"error": "Permission denied"})
    return {"status": "ok"}


@router.post("/api/files/upload")
async def files_upload(path: str = Form(...), file: UploadFile = File(...)):
    try:
        dir_path = _content_access_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    if not dir_path.is_dir():
        return JSONResponse(status_code=400, content={"error": "Target is not a directory"})
    safe_name = Path(file.filename or "upload").name
    if not safe_name or safe_name in (".", ".."):
        return JSONResponse(status_code=400, content={"error": "Invalid filename"})
    dest = dir_path / safe_name
    try:
        dest.write_bytes(await file.read())
    except PermissionError:
        return JSONResponse(status_code=403, content={"error": "Permission denied"})
    stat = dest.stat()
    rel = _normalize_files_repo_path(dest)
    if rel is None:
        return JSONResponse(status_code=400, content={"error": "Path outside project root"})
    return {
        "status": "ok",
        "id": rel,
        "size": stat.st_size,
        "date": int(stat.st_mtime * 1000),
    }


@router.post("/api/files/rename")
async def files_rename(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    old_id = str(payload.get("id") or "").strip()
    new_name = str(payload.get("name") or "").strip()
    if not old_id or not new_name:
        return JSONResponse(status_code=400, content={"error": "id and name are required"})
    if "/" in new_name or "\\" in new_name:
        return JSONResponse(status_code=400, content={"error": "name must not contain path separators"})
    if _is_virtual_file_root(old_id):
        return JSONResponse(status_code=400, content={"error": "Cannot rename file manager root"})
    try:
        old_path = _content_access_path(old_id)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    if not old_path.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    new_path = old_path.parent / new_name
    root = _file_manager_root_for_absolute_path(old_path)
    if root is None:
        return JSONResponse(status_code=400, content={"error": "Target outside project root"})
    new_path_resolved = new_path.resolve()
    root_path = Path(root["path"])
    if not _path_is_within_root(new_path_resolved, root_path):
        return JSONResponse(status_code=400, content={"error": "Target outside project root"})
    relative = _relative_path_within_file_root(new_path_resolved)
    if relative in _PROTECTED_FILE_CONTENT_PATHS:
        return JSONResponse(status_code=403, content={"error": "Permission denied"})
    try:
        old_path.rename(new_path)
    except PermissionError:
        return JSONResponse(status_code=403, content={"error": "Permission denied"})
    new_id = _normalize_files_repo_path(new_path)
    if new_id is None:
        return JSONResponse(status_code=400, content={"error": "Target outside project root"})
    return {"status": "ok", "newId": new_id}


@router.post("/api/files/delete")
async def files_delete(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return JSONResponse(status_code=400, content={"error": "ids must be a non-empty list"})
    errors = []
    for raw_id in ids:
        if _is_virtual_file_root(str(raw_id)):
            errors.append("Cannot delete file manager root")
            continue
        try:
            p = _content_access_path(str(raw_id))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        except PermissionError as exc:
            errors.append(str(exc))
            continue
        if not p.exists():
            continue
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        except OSError as exc:
            errors.append(str(exc))
    if errors:
        return JSONResponse(status_code=400, content={"error": "; ".join(errors)})
    return {"status": "ok"}


@router.post("/api/files/copy")
async def files_copy(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    ids = payload.get("ids") or []
    target = str(payload.get("target") or "").strip()
    if not ids or not target:
        return JSONResponse(status_code=400, content={"error": "ids and target are required"})
    try:
        target_path = _content_access_path(target)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    if not target_path.is_dir():
        return JSONResponse(status_code=400, content={"error": "Target is not a directory"})
    new_ids = []
    for raw_id in ids:
        if _is_virtual_file_root(str(raw_id)):
            return JSONResponse(status_code=400, content={"error": "Cannot copy file manager root"})
        try:
            src = _content_access_path(str(raw_id))
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        except PermissionError as exc:
            return JSONResponse(status_code=403, content={"error": str(exc)})
        dest = target_path / src.name
        counter = 1
        orig = dest
        while dest.exists():
            dest = orig.parent / f"{orig.stem}_copy{counter}{orig.suffix}"
            counter += 1
        relative = _relative_path_within_file_root(dest)
        if relative in _PROTECTED_FILE_CONTENT_PATHS:
            return JSONResponse(status_code=403, content={"error": "Permission denied"})
        try:
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
        except PermissionError:
            return JSONResponse(status_code=403, content={"error": "Permission denied"})
        normalized = _normalize_files_repo_path(dest)
        if normalized is None:
            return JSONResponse(status_code=400, content={"error": "Path outside project root"})
        new_ids.append(normalized)
    return {"status": "ok", "newIds": new_ids}


@router.post("/api/files/move")
async def files_move(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    ids = payload.get("ids") or []
    target = str(payload.get("target") or "").strip()
    if not ids or not target:
        return JSONResponse(status_code=400, content={"error": "ids and target are required"})
    try:
        target_path = _content_access_path(target)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    if not target_path.is_dir():
        return JSONResponse(status_code=400, content={"error": "Target is not a directory"})
    new_ids = []
    for raw_id in ids:
        if _is_virtual_file_root(str(raw_id)):
            return JSONResponse(status_code=400, content={"error": "Cannot move file manager root"})
        try:
            src = _content_access_path(str(raw_id))
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        except PermissionError as exc:
            return JSONResponse(status_code=403, content={"error": str(exc)})
        dest = target_path / src.name
        # Fix #10: handle destination collision (same as files_copy)
        if dest.resolve() != src.resolve() and dest.exists():
            counter = 1
            orig = dest
            while dest.exists():
                dest = orig.parent / f"{orig.stem}_moved{counter}{orig.suffix}"
                counter += 1
        relative = _relative_path_within_file_root(dest)
        if relative in _PROTECTED_FILE_CONTENT_PATHS:
            return JSONResponse(status_code=403, content={"error": "Permission denied"})
        try:
            shutil.move(str(src), str(dest))
        except PermissionError:
            return JSONResponse(status_code=403, content={"error": "Permission denied"})
        normalized = _normalize_files_repo_path(dest)
        if normalized is None:
            return JSONResponse(status_code=400, content={"error": "Path outside project root"})
        new_ids.append(normalized)
    return {"status": "ok", "newIds": new_ids}


@router.post("/api/files/mkdir")
async def files_mkdir(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    parent = str(payload.get("parent") or "").strip()
    name = str(payload.get("name") or "").strip()
    if not parent or not name:
        return JSONResponse(status_code=400, content={"error": "parent and name are required"})
    if "/" in name or "\\" in name:
        return JSONResponse(status_code=400, content={"error": "name must not contain path separators"})
    if parent == "/" and _file_manager_multi_root_enabled():
        return JSONResponse(status_code=400, content={"error": "Cannot create folders in the virtual root"})
    try:
        parent_path = _content_access_path(parent)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    new_dir = parent_path / name
    root = _file_manager_root_for_absolute_path(parent_path)
    if root is None:
        return JSONResponse(status_code=400, content={"error": "Target outside project root"})
    new_dir_resolved = new_dir.resolve()
    root_path = Path(root["path"])
    if not _path_is_within_root(new_dir_resolved, root_path):
        return JSONResponse(status_code=400, content={"error": "Target outside project root"})
    try:
        new_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return JSONResponse(status_code=403, content={"error": "Permission denied"})
    new_id = _normalize_files_repo_path(new_dir)
    if new_id is None:
        return JSONResponse(status_code=400, content={"error": "Path outside project root"})
    return {"status": "ok", "id": new_id}


@router.get("/api/files/download")
def files_download(path: str):
    try:
        file_path = _content_access_path(path)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    if not file_path.exists() or not file_path.is_file():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(str(file_path), filename=file_path.name)


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def _file_stream_status_payload() -> dict[str, Any]:
    return {
        "timestamp": int(time.time() * 1000),
        "watcher": _FILE_REALTIME_HUB.status(),
    }


@router.get("/api/files/events")
async def files_events(
    request: Request,
    dir: str = "/",
    file: str | None = None,
):
    try:
        normalized_dir = _safe_files_path(dir)
        dir_id = _normalize_files_repo_path(normalized_dir)
        if dir_id is None:
            raise ValueError("Path outside project root")
        file_id: str | None = None
        if file:
            normalized_file = _safe_files_path(file)
            file_id = _normalize_files_repo_path(normalized_file)
            if file_id is None:
                raise ValueError("Path outside project root")
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
    loop = asyncio.get_running_loop()
    subscriber_id = _FILE_REALTIME_HUB.subscribe(
        dir_path=dir_id,
        file_path=file_id,
        queue=queue,
        loop=loop,
    )

    async def event_stream():
        try:
            yield _format_sse("ready", _file_stream_status_payload())
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield _format_sse("change", event)
                except asyncio.TimeoutError:
                    yield _format_sse("heartbeat", _file_stream_status_payload())
        finally:
            _FILE_REALTIME_HUB.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
