#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

_ENGINE_ROOT = str(Path(__file__).resolve().parents[1])
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

import json5_io as json5


class SubagentInstallError(RuntimeError):
    pass


SUPPORTED_TARGETS = ("claude", "codex", "gemini", "opencode")
SUPPORTED_FRONTMATTER_KEYS = {"name", "description"}
VALID_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True)
class SubagentDefinition:
    name: str
    description: str
    body: str
    source_path: Path
    level: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install Skill Pilot subagents into supported coding-agent subagent folders."
    )
    parser.add_argument(
        "--source",
        nargs="*",
        default=None,
        help="Source subagent root(s) (default: <repo>/core/subagents/system and <repo>/core/subagents/user).",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root where coding-agent subagent folders are written (default: repo root).",
    )
    parser.add_argument(
        "--disabled-config",
        default=None,
        help="JSON5 file containing disabled subagent names array (default: <repo>/config/disabled_subagents.json5).",
    )
    parser.add_argument(
        "--targets",
        default=",".join(SUPPORTED_TARGETS),
        help=f"Comma-separated install targets. Supported: {', '.join(SUPPORTED_TARGETS)}.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--all",
        action="store_true",
        help="Install all discovered subagents, respecting disabled_subagents config (default).",
    )
    mode.add_argument(
        "--add",
        metavar="SUBAGENT",
        default=None,
        help="Install a single named subagent, ignoring disabled_subagents. Leaves other installed subagents untouched.",
    )
    mode.add_argument(
        "--subagents",
        metavar="LIST",
        default=None,
        help=(
            "Comma-separated list of subagents to install exclusively, ignoring disabled_subagents. "
            "Removes any installed Skill Pilot subagents not in the list."
        ),
    )
    return parser.parse_args()


def load_disabled_subagents(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        raw = json5.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SubagentInstallError(f"Invalid JSON5 in disabled subagents config: {path}") from exc
    if not isinstance(raw, list):
        raise SubagentInstallError("disabled_subagents config must be a JSON array of subagent names")

    disabled: set[str] = set()
    for value in raw:
        if isinstance(value, str) and value.strip():
            disabled.add(value.strip())
    return disabled


def split_markdown_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        raise SubagentInstallError(f"Missing YAML frontmatter: {path}")

    end = text.find("\n---", 3)
    if end == -1:
        raise SubagentInstallError(f"Unterminated YAML frontmatter: {path}")

    frontmatter_text = text[3:end].strip()
    body = text[end + len("\n---") :].lstrip("\r\n")

    try:
        raw = yaml.safe_load(frontmatter_text) if frontmatter_text else {}
    except yaml.YAMLError as exc:
        raise SubagentInstallError(f"Invalid YAML frontmatter in {path}") from exc
    if not isinstance(raw, dict):
        raise SubagentInstallError(f"Frontmatter must be a mapping: {path}")
    return raw, body


def parse_subagent(path: Path, source_root: Path) -> SubagentDefinition:
    raw_meta, body = split_markdown_frontmatter(path)
    meta = {str(key): value for key, value in raw_meta.items()}
    unsupported = sorted(set(meta) - SUPPORTED_FRONTMATTER_KEYS)
    if unsupported:
        raise SubagentInstallError(
            f"Unsupported frontmatter key(s) in {path}: {', '.join(unsupported)}. "
            "First-stage subagents only support name and description."
        )

    name = str(meta.get("name", "")).strip()
    description = str(meta.get("description", "")).strip()
    if not name:
        raise SubagentInstallError(f"Subagent frontmatter requires name: {path}")
    if not description:
        raise SubagentInstallError(f"Subagent frontmatter requires description: {path}")
    if not VALID_NAME_RE.match(name):
        raise SubagentInstallError(
            f"Invalid subagent name '{name}' in {path}. Use lowercase letters, numbers, hyphens, and underscores."
        )

    level = source_root.name
    return SubagentDefinition(name=name, description=description, body=body.rstrip() + "\n", source_path=path, level=level)


def discover_subagents(source_root: Path) -> list[SubagentDefinition]:
    if not source_root.exists():
        return []
    definitions: list[SubagentDefinition] = []
    for path in sorted(source_root.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(source_root).parts):
            continue
        definitions.append(parse_subagent(path, source_root))
    return definitions


def build_claude_or_gemini_markdown(subagent: SubagentDefinition) -> str:
    return (
        "---\n"
        f"name: {subagent.name}\n"
        f"description: {quote_yaml_scalar(subagent.description)}\n"
        "---\n"
        f"{subagent.body}"
    )


def build_opencode_markdown(subagent: SubagentDefinition) -> str:
    return (
        "---\n"
        f"description: {quote_yaml_scalar(subagent.description)}\n"
        "mode: subagent\n"
        "---\n"
        f"{subagent.body}"
    )


def build_codex_toml(subagent: SubagentDefinition) -> str:
    return (
        f'name = "{escape_toml_string(subagent.name)}"\n'
        f'description = "{escape_toml_string(subagent.description)}"\n\n'
        'developer_instructions = """\n'
        f"{escape_toml_multiline(subagent.body)}"
        '"""\n'
    )


def quote_yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def escape_toml_multiline(value: str) -> str:
    return value.replace('"""', '\\"\\"\\"')


def target_file(project_root: Path, target: str, name: str) -> Path:
    if target == "claude":
        return project_root / ".claude" / "agents" / f"{name}.md"
    if target == "codex":
        return project_root / ".codex" / "agents" / f"{name}.toml"
    if target == "gemini":
        return project_root / ".gemini" / "agents" / f"{name}.md"
    if target == "opencode":
        return project_root / ".opencode" / "agents" / f"{name}.md"
    raise SubagentInstallError(f"Unsupported target: {target}")


def render_target(target: str, subagent: SubagentDefinition) -> str:
    if target in {"claude", "gemini"}:
        return build_claude_or_gemini_markdown(subagent)
    if target == "codex":
        return build_codex_toml(subagent)
    if target == "opencode":
        return build_opencode_markdown(subagent)
    raise SubagentInstallError(f"Unsupported target: {target}")


def write_text_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8", errors="replace") == content:
        return False
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)
    return True


def remove_generated_target(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True


def parse_targets(value: str) -> list[str]:
    targets = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(targets) - set(SUPPORTED_TARGETS))
    if unknown:
        raise SubagentInstallError(f"Unknown target(s): {', '.join(unknown)}")
    return targets


def installed_target_names(project_root: Path, target: str) -> set[str]:
    if target == "claude":
        target_root = project_root / ".claude" / "agents"
        suffix = ".md"
    elif target == "codex":
        target_root = project_root / ".codex" / "agents"
        suffix = ".toml"
    elif target == "gemini":
        target_root = project_root / ".gemini" / "agents"
        suffix = ".md"
    elif target == "opencode":
        target_root = project_root / ".opencode" / "agents"
        suffix = ".md"
    else:
        raise SubagentInstallError(f"Unsupported target: {target}")

    if not target_root.exists():
        return set()
    return {path.stem for path in target_root.iterdir() if path.is_file() and path.suffix == suffix}


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    default_sources = [repo_root / "core" / "subagents" / "system", repo_root / "core" / "subagents" / "user"]
    source_roots = [Path(s).expanduser().resolve() for s in args.source] if args.source else default_sources
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else repo_root
    disabled_config = (
        Path(args.disabled_config).expanduser().resolve()
        if args.disabled_config
        else repo_root / "config" / "disabled_subagents.json5"
    )

    try:
        targets = parse_targets(args.targets)
    except SubagentInstallError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    requested_names: set[str] | None = None
    if args.add is not None:
        name = args.add.strip()
        if not name:
            print("--add requires a non-empty subagent name", file=sys.stderr)
            return 2
        requested_names = {name}
        mode = "add"
    elif args.subagents is not None:
        requested_names = {n.strip() for n in args.subagents.split(",") if n.strip()}
        if not requested_names:
            print("--subagents requires a non-empty comma-separated list", file=sys.stderr)
            return 2
        mode = "subagents"
    else:
        mode = "all"

    try:
        disabled_subagents = load_disabled_subagents(disabled_config) if mode == "all" else set()
        all_subagents: list[SubagentDefinition] = []
        for source_root in source_roots:
            all_subagents.extend(discover_subagents(source_root))
    except SubagentInstallError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    seen: dict[str, SubagentDefinition] = {}
    duplicates: list[str] = []
    for subagent in all_subagents:
        if subagent.name in seen:
            duplicates.append(f"  - {subagent.name}: {seen[subagent.name].source_path} vs {subagent.source_path}")
        else:
            seen[subagent.name] = subagent
    if duplicates:
        print("Duplicate subagent name(s) found across source roots:", file=sys.stderr)
        for line in duplicates:
            print(line, file=sys.stderr)
        return 2

    if requested_names is not None:
        unknown = sorted(n for n in requested_names if n not in seen)
        if unknown:
            print(f"Unknown subagent name(s): {', '.join(unknown)}", file=sys.stderr)
            return 2

    if mode == "all":
        install_names = sorted(name for name in seen if name not in disabled_subagents)
        remove_names = sorted(name for name in disabled_subagents if name in seen)
    else:
        install_names = sorted(requested_names or set())
        remove_names = [] if mode == "add" else sorted(set(seen) - set(install_names))

    installed: list[str] = []
    unchanged: list[str] = []
    removed: list[str] = []
    failed: list[tuple[str, str, str]] = []

    for target in targets:
        target_remove_names = set(remove_names)
        if mode in {"all", "subagents"}:
            target_remove_names.update(installed_target_names(project_root, target) - set(install_names))

        for name in sorted(target_remove_names):
            path = target_file(project_root, target, name)
            try:
                if remove_generated_target(path):
                    removed.append(f"{target}:{name}")
            except OSError as exc:
                failed.append((target, name, str(exc)))

    for name in install_names:
        subagent = seen[name]
        for target in targets:
            path = target_file(project_root, target, name)
            try:
                changed = write_text_if_changed(path, render_target(target, subagent))
            except OSError as exc:
                failed.append((target, name, str(exc)))
                continue
            if changed:
                installed.append(f"{target}:{name}")
            else:
                unchanged.append(f"{target}:{name}")

    sources_label = ", ".join(str(s) for s in source_roots)
    print(f"Mode: {mode}. Discovered {len(all_subagents)} subagent(s) under [{sources_label}].")
    print(f"Targets: {', '.join(targets)}")
    print(f"Installed or updated {len(installed)} target file(s) under {project_root}.")
    if unchanged:
        print(f"Unchanged {len(unchanged)} target file(s).")
    if removed:
        print(f"Removed {len(removed)} disabled/excluded target file(s): {', '.join(removed)}")
    skipped_disabled = sorted(name for name in seen if name in disabled_subagents)
    if skipped_disabled:
        print(f"Skipped {len(skipped_disabled)} disabled subagent(s): {', '.join(skipped_disabled)}")
    if failed:
        print(f"Failed for {len(failed)} target file(s):")
        for target, name, detail in failed:
            print(f"  - {target}:{name}: {detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
