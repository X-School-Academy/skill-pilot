from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IgnoreRule:
    base_dir: Path
    pattern: str
    directory_only: bool = False


class IgnoreRules:
    def __init__(self) -> None:
        self._rules: list[IgnoreRule] = []

    def load_from_directory(self, directory: Path) -> None:
        for item in sorted(directory.iterdir(), key=lambda path: path.name):
            if not item.is_file():
                continue
            if "ignore" not in item.name.lower():
                continue
            self.load_file(item)

    def load_file(self, path: Path) -> None:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            # Security posture: ignore negated rules instead of re-including files.
            if line.startswith("!"):
                continue
            directory_only = line.endswith("/")
            pattern = line.rstrip("/")
            if pattern:
                self._rules.append(IgnoreRule(path.parent.resolve(), pattern, directory_only))

    def is_ignored(self, path: Path, *, is_dir: bool | None = None) -> bool:
        resolved = path.resolve()
        for rule in self._rules:
            if rule.directory_only and is_dir is False:
                continue
            try:
                rel = resolved.relative_to(rule.base_dir)
            except ValueError:
                continue
            rel_text = rel.as_posix()
            name = resolved.name
            pattern = rule.pattern
            if pattern.startswith("/"):
                candidate = pattern.lstrip("/")
                if fnmatch.fnmatch(rel_text, candidate):
                    return True
                continue
            if "/" in pattern:
                if fnmatch.fnmatch(rel_text, pattern):
                    return True
                continue
            if fnmatch.fnmatch(name, pattern):
                return True
            if any(fnmatch.fnmatch(part, pattern) for part in rel.parts):
                return True
        return False
