#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import json5
import os
import subprocess
import sys
from pathlib import Path


class SkillInstallError(RuntimeError):
    pass


EXCLUDED_SOURCE_DIR_NAMES = {"alternatives"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install local skills by validating and linking into .agent/skills.")
    parser.add_argument(
        "--source",
        nargs="*",
        default=None,
        help="Source skills root(s) (default: <repo>/core/skills and <repo>/dev-swarm/skills).",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Destination skills directory (default: <repo>/.agent/skills).",
    )
    parser.add_argument(
        "--disabled-config",
        default=None,
        help="JSON file containing disabled skill names array (default: <repo>/config/disabled_skills.json5).",
    )
    parser.add_argument(
        "--verify-bin",
        default=None,
        help="Skill verify executable path (default: <repo>/core/bin/skill-verify).",
    )
    return parser.parse_args()


def load_disabled_skills(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        raw = json5.loads(path.read_text())
    except Exception as exc:
        raise SkillInstallError(f"Invalid JSON in disabled skills config: {path}") from exc
    if not isinstance(raw, list):
        raise SkillInstallError("disabled_skills config must be a JSON array of skill names")

    disabled: set[str] = set()
    for value in raw:
        if isinstance(value, str) and value.strip():
            disabled.add(value.strip())
    return disabled


def should_exclude_path(path: Path, source_root: Path) -> bool:
    try:
        relative_parts = path.resolve().relative_to(source_root.resolve()).parts
    except ValueError:
        return False
    return any(part in EXCLUDED_SOURCE_DIR_NAMES for part in relative_parts)


def discover_skills(source_root: Path) -> list[Path]:
    if not source_root.exists():
        return []
    discovered: list[Path] = []
    for skill_md in source_root.rglob("SKILL.md"):
        if should_exclude_path(skill_md.parent, source_root):
            continue
        discovered.append(skill_md.parent)
    return sorted(discovered)


def run_verify(verify_bin: Path, skill_dir: Path) -> tuple[bool, str]:
    command = [str(verify_bin), str(skill_dir)]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise SkillInstallError(f"Failed to execute skill verifier: {verify_bin}") from exc
    output = "\n".join(
        part.strip() for part in [completed.stdout, completed.stderr] if isinstance(part, str) and part.strip()
    )
    return completed.returncode == 0, output


def ensure_symlink(source_dir: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    resolved_source = source_dir.resolve()
    relative_source = Path(os.path.relpath(resolved_source, destination.parent))

    if destination.is_symlink():
        existing_target = destination.resolve()
        if existing_target == resolved_source:
            return
        destination.unlink()
    elif destination.exists():
        raise SkillInstallError(f"Destination exists and is not a symlink: {destination}")

    destination.symlink_to(relative_source, target_is_directory=True)


def remove_broken_symlinks(target_root: Path) -> list[str]:
    removed: list[str] = []
    if not target_root.exists():
        return removed
    for entry in sorted(target_root.iterdir()):
        if entry.is_symlink() and not entry.resolve().exists():
            entry.unlink()
            removed.append(entry.name)
    return removed


def remove_excluded_symlinks(target_root: Path, source_roots: list[Path]) -> list[str]:
    removed: list[str] = []
    if not target_root.exists():
        return removed

    resolved_roots = [source_root.resolve() for source_root in source_roots]
    for entry in sorted(target_root.iterdir()):
        if not entry.is_symlink():
            continue
        target = entry.resolve()
        if any(should_exclude_path(target, source_root) for source_root in resolved_roots):
            entry.unlink()
            removed.append(entry.name)
    return removed


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[4]
    default_sources = [repo_root / "core" / "skills", repo_root / "dev-swarm" / "skills"]
    source_roots = [Path(s).expanduser().resolve() for s in args.source] if args.source else default_sources
    target_root = Path(args.target).expanduser().resolve() if args.target else repo_root / ".agent" / "skills"
    disabled_config = (
        Path(args.disabled_config).expanduser().resolve()
        if args.disabled_config
        else repo_root / "config" / "disabled_skills.json5"
    )
    verify_bin = (
        Path(args.verify_bin).expanduser().resolve() if args.verify_bin else repo_root / "core" / "bin" / "skill-verify"
    )

    if not verify_bin.exists():
        print(f"skill verifier not found: {verify_bin}", file=sys.stderr)
        return 2

    try:
        disabled_skills = load_disabled_skills(disabled_config)
    except SkillInstallError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    removed_broken = remove_broken_symlinks(target_root)
    removed_excluded = remove_excluded_symlinks(target_root, source_roots)

    all_skill_dirs: list[Path] = []
    for source_root in source_roots:
        all_skill_dirs.extend(discover_skills(source_root))

    seen: dict[str, Path] = {}
    duplicates: list[str] = []
    for skill_dir in all_skill_dirs:
        name = skill_dir.name
        if name in seen:
            duplicates.append(f"  - {name}: {seen[name]} vs {skill_dir}")
        else:
            seen[name] = skill_dir
    if duplicates:
        print("Duplicate skill name(s) found across source roots:", file=sys.stderr)
        for line in duplicates:
            print(line, file=sys.stderr)
        return 2

    installed: list[str] = []
    skipped_disabled: list[str] = []
    failed_verify: list[tuple[str, str]] = []
    failed_link: list[tuple[str, str]] = []

    for skill_dir in all_skill_dirs:
        skill_name = skill_dir.name
        if skill_name in disabled_skills:
            skipped_disabled.append(skill_name)
            continue

        ok, output = run_verify(verify_bin, skill_dir)
        if not ok:
            failed_verify.append((skill_name, output))
            continue

        try:
            ensure_symlink(skill_dir, target_root / skill_name)
            installed.append(skill_name)
        except Exception as exc:
            failed_link.append((skill_name, str(exc)))

    sources_label = ", ".join(str(s) for s in source_roots)
    print(f"Discovered {len(all_skill_dirs)} skill(s) under [{sources_label}].")
    print(f"Installed {len(installed)} skill(s) into {target_root}.")
    if removed_broken:
        print(f"Removed {len(removed_broken)} broken symlink(s): {', '.join(removed_broken)}")
    if removed_excluded:
        print(f"Removed {len(removed_excluded)} excluded symlink(s): {', '.join(removed_excluded)}")
    if skipped_disabled:
        print(f"Skipped {len(skipped_disabled)} disabled skill(s).")
    if failed_verify:
        print(f"Failed verify for {len(failed_verify)} skill(s):")
        for skill_name, output in failed_verify:
            print(f"  - {skill_name}")
            if output:
                print(f"    {output.replace(chr(10), chr(10) + '    ')}")
    if failed_link:
        print(f"Failed link for {len(failed_link)} skill(s):")
        for skill_name, detail in failed_link:
            print(f"  - {skill_name}: {detail}")

    if failed_verify or failed_link:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
