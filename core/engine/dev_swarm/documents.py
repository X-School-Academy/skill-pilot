import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

from .project import get_project_root
from .stages import STAGES

ALLOWED_EXTENSIONS = {".md", ".html"}
ALLOWED_ASSET_EXTENSIONS = {
    ".html",
    ".css",
    ".js",
    ".mjs",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".txt",
}
WRITABLE_ROOT_FILES = {"ideas.md"}


def _allowed_dirs() -> set[str]:
    return {stage.directory for stage in STAGES}


def resolve_path(file_path: str) -> Path:
    if not file_path or not file_path.strip():
        raise ValueError("Path is required")
    if Path(file_path).is_absolute():
        raise ValueError("Absolute paths are not allowed")
    parts = Path(file_path).parts
    if ".." in parts:
        raise ValueError("Path traversal is not allowed")

    root = get_project_root()
    resolved = (root / file_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Path is outside project root") from exc
    return resolved


def _ensure_scope(resolved: Path, for_write: bool) -> None:
    root = get_project_root()
    relative = resolved.relative_to(root)
    parts = relative.parts
    if not parts:
        if for_write:
            raise ValueError("Writes must target stage directories or allowed root files")
        raise ValueError("Reads must target stage directories or allowed root files")

    if len(parts) == 1 and parts[0] in WRITABLE_ROOT_FILES:
        return

    if parts[0] not in _allowed_dirs():
        if for_write:
            raise ValueError("Writes must target stage directories")
        raise ValueError("Reads must target stage directories")


def _content_type(path: Path) -> str:
    return "text/html" if path.suffix.lower() == ".html" else "text/markdown"


def _asset_content_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".mjs":
        return "text/javascript; charset=utf-8"
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed is None:
        return "application/octet-stream"
    if guessed.startswith("text/") and "charset" not in guessed:
        return f"{guessed}; charset=utf-8"
    return guessed


def _iso_mtime(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def read_document(file_path: str) -> Dict[str, str]:
    resolved = resolve_path(file_path)
    if not resolved.exists():
        raise FileNotFoundError("Document not found")

    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported document type")
    _ensure_scope(resolved, for_write=False)

    content = resolved.read_text(encoding="utf-8", errors="replace")
    root = get_project_root()
    return {
        "path": resolved.relative_to(root).as_posix(),
        "content": content,
        "contentType": _content_type(resolved),
        "lastModified": _iso_mtime(resolved),
    }


def write_document(file_path: str, content: str) -> Dict[str, str]:
    resolved = resolve_path(file_path)
    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported document type")
    _ensure_scope(resolved, for_write=True)

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    root = get_project_root()
    return {
        "path": resolved.relative_to(root).as_posix(),
        "content": content,
        "contentType": _content_type(resolved),
        "lastModified": _iso_mtime(resolved),
    }


def delete_document(file_path: str) -> None:
    resolved = resolve_path(file_path)
    if not resolved.exists():
        raise FileNotFoundError("Document not found")
    if resolved.name == "README.md":
        raise ValueError("README.md cannot be deleted")
    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported document type")
    _ensure_scope(resolved, for_write=True)

    resolved.unlink()


def read_asset(file_path: str) -> Tuple[bytes, str]:
    resolved = resolve_path(file_path)
    if not resolved.exists():
        raise FileNotFoundError("Document not found")
    if resolved.is_dir():
        raise ValueError("Path is a directory")
    if resolved.suffix.lower() not in ALLOWED_ASSET_EXTENSIONS:
        raise ValueError("Unsupported asset type")
    _ensure_scope(resolved, for_write=False)

    return resolved.read_bytes(), _asset_content_type(resolved)
