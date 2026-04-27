from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .ignore_rules import IgnoreRules


@dataclass(frozen=True)
class SkillDocument:
    name: str
    path: Path
    content: str


_FRONTMATTER_NAME_RE = re.compile(r"^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$", re.MULTILINE)


def _skill_name(path: Path, content: str) -> str:
    match = _FRONTMATTER_NAME_RE.search(content)
    if match:
        return match.group(1).strip()
    return path.parent.name


def _selected_names(raw: str | None) -> set[str] | None:
    if raw is None or not raw.strip():
        return None
    names = {item.strip() for item in raw.split(",") if item.strip()}
    return names or None


def discover_skills(skills_dir: Path) -> list[SkillDocument]:
    root = skills_dir.resolve()
    if not root.exists() or not root.is_dir():
        return []

    rules = IgnoreRules()
    documents: list[SkillDocument] = []
    for current_root, dir_names, file_names in os.walk(root):
        current = Path(current_root)
        rules.load_from_directory(current)
        dir_names[:] = [
            name
            for name in sorted(dir_names)
            if not rules.is_ignored(current / name, is_dir=True)
        ]
        if "SKILL.md" not in file_names:
            continue
        skill_path = current / "SKILL.md"
        if rules.is_ignored(skill_path, is_dir=False):
            continue
        try:
            content = skill_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            continue
        if not content:
            continue
        documents.append(SkillDocument(_skill_name(skill_path, content), skill_path, content))
    return sorted(documents, key=lambda doc: doc.name)


def load_skill_instructions(skills_dir: Path, skills: str | None = None) -> str:
    selected = _selected_names(skills)
    documents = discover_skills(skills_dir)
    if selected is not None:
        documents = [
            doc
            for doc in documents
            if doc.name in selected or doc.path.parent.name in selected
        ]

    sections: list[str] = []
    for doc in documents:
        try:
            rel_path = doc.path.relative_to(skills_dir.resolve()).as_posix()
        except ValueError:
            rel_path = str(doc.path)
        sections.append(f"## {doc.name} ({rel_path})\n\n{doc.content}")

    if not sections:
        return ""
    return "# Skill Instructions\n\n" + "\n\n".join(sections)
