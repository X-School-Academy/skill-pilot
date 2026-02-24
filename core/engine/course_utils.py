import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import HTTPException

from settings import COURSES_DIR


def safe_course_path(course: str) -> Path:
    if not course:
        raise HTTPException(status_code=400, detail="Missing course path")
    candidate = (COURSES_DIR / course).resolve()
    if not str(candidate).startswith(str(COURSES_DIR)):
        raise HTTPException(status_code=400, detail="Invalid course path")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Course not found")
    return candidate


def build_tree(path: Path) -> list:
    items = []
    for entry in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if entry.name.startswith("."):
            continue
        stat = entry.stat()
        if entry.is_dir():
            children = build_tree(entry)
            mtime = max([stat.st_mtime] + [c["mtime"] for c in children]) if children else stat.st_mtime
            items.append(
                {
                    "name": entry.name,
                    "path": str(entry.relative_to(COURSES_DIR)),
                    "type": "dir",
                    "mtime": mtime,
                    "children": children,
                }
            )
        else:
            items.append(
                {
                    "name": entry.name,
                    "path": str(entry.relative_to(COURSES_DIR)),
                    "type": "file",
                    "mtime": stat.st_mtime,
                }
            )
    return items


def find_latest_course(path: Path) -> Optional[tuple[str, float]]:
    latest_path = None
    latest_mtime = 0.0
    for entry in path.rglob("*"):
        if not entry.is_file():
            continue
        if entry.name.startswith("."):
            continue
        mtime = entry.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_path = entry
    if latest_path is None:
        return None
    return str(latest_path.relative_to(COURSES_DIR)), latest_mtime


def _meta_block_match(text: str) -> Optional[re.Match]:
    pattern = re.compile(r"```yaml\s*(\{[^\n]*\})?\s*\n(.*?)\n```", re.DOTALL)
    for match in pattern.finditer(text):
        header = (match.group(1) or "").strip()
        if '"type"' in header and "meta" in header:
            return match
        if "type: meta" in match.group(2):
            return match
    return None


def read_course_meta(text: str) -> Dict[str, Any]:
    match = _meta_block_match(text)
    if not match:
        return {}
    yaml_body = match.group(2)
    try:
        data = yaml.safe_load(yaml_body)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_course_meta(text: str, updates: Dict[str, Any]) -> str:
    match = _meta_block_match(text)
    meta: Dict[str, Any] = {}
    header = '{"type":"meta"}'
    if match:
        header = (match.group(1) or header).strip()
        yaml_body = match.group(2)
        try:
            parsed = yaml.safe_load(yaml_body)
            if isinstance(parsed, dict):
                meta.update(parsed)
        except Exception:
            pass
        span = match.span()
    else:
        span = (0, 0)

    meta.update(updates)
    new_yaml = yaml.safe_dump(meta, sort_keys=False).strip()
    new_block = f"```yaml {header}\n{new_yaml}\n```"

    if match:
        remainder = text[span[1] :]
        remainder = remainder.lstrip("\n")
        return text[: span[0]] + new_block + "\n\n" + remainder
    remainder = text.lstrip("\n")
    return new_block + "\n\n" + remainder
