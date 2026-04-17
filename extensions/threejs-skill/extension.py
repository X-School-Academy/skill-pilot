from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


EXTENSION_DIR = Path(__file__).resolve().parent
EXTENSION_JSON5 = EXTENSION_DIR / "extension.json5"
REPO_ROOT = EXTENSION_DIR.parents[1]
TEMP_ROOT = REPO_ROOT / ".skillpilot" / "temp"
USER_SKILLS_DIR = REPO_ROOT / "core" / "skills" / "user"
SKILL_VERIFY_BIN = REPO_ROOT / "core" / "bin" / "skill-verify"
SKILL_INSTALL_BIN = REPO_ROOT / "core" / "bin" / "skill-install"
REPO_URL = "https://github.com/X-School-Academy/extension-threejs-skills.git"
REPO_DIR_NAME = "extension-threejs-skills"


def _timestamp() -> str:
    return str(int(time.time()))


def _run_dir(action: str) -> Path:
    path = TEMP_ROOT / f"{EXTENSION_DIR.name}-{action}-{_timestamp()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_command(args: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=False,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _write_summary(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _set_installed(value: bool) -> None:
    """Update the ``installed`` field in extension.json5."""
    if not EXTENSION_JSON5.is_file():
        return
    import re
    text = EXTENSION_JSON5.read_text(encoding="utf-8")
    if re.search(r"installed\s*:", text):
        text = re.sub(r"(installed\s*:\s*)(true|false)", rf"\g<1>{'true' if value else 'false'}", text)
    else:
        # Insert before the closing brace
        text = re.sub(r"(\s*)\}", rf"\1  installed: {'true' if value else 'false'},\n\1}}", text)
    EXTENSION_JSON5.write_text(text, encoding="utf-8")


def _clone_repo(run_dir: Path) -> tuple[Path | None, str]:
    repo_path = run_dir / REPO_DIR_NAME
    code, output = _run_command(
        ["git", "clone", "--depth", "1", REPO_URL, str(repo_path)],
        REPO_ROOT,
    )
    if code != 0:
        return None, output
    return repo_path, output


def _find_threejs_skills(repo_path: Path) -> list[Path]:
    skills_root = repo_path / "skills"
    if not skills_root.is_dir():
        return []
    matches: list[Path] = []
    for child in sorted(skills_root.iterdir()):
        if child.is_dir() and child.name.startswith("threejs-") and (child / "SKILL.md").is_file():
            matches.append(child)
    return matches


def _copy_skill(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def install_or_update(action: str) -> int:
    run_dir = _run_dir(action)
    repo_path, clone_output = _clone_repo(run_dir)
    if repo_path is None:
        print(clone_output, file=sys.stderr)
        return 1

    source_skills = _find_threejs_skills(repo_path)
    if not source_skills:
        print("No threejs-* skills found in cloned repository.", file=sys.stderr)
        return 1

    USER_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    installed_targets: list[Path] = []
    backups_dir = run_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    for src in source_skills:
        target = USER_SKILLS_DIR / src.name
        if target.exists():
            backup_target = backups_dir / src.name
            if backup_target.exists():
                shutil.rmtree(backup_target)
            shutil.copytree(target, backup_target)
        _copy_skill(src, target)
        installed_targets.append(target)

    verify_code, verify_output = _run_command(
        [str(SKILL_VERIFY_BIN), *[str(path) for path in installed_targets]],
        REPO_ROOT,
    )
    install_code, install_output = _run_command([str(SKILL_INSTALL_BIN)], REPO_ROOT)
    combined_output = clone_output + verify_output + install_output
    _write_summary(
        run_dir / f"{action}-summary.json",
        {
            "action": action,
            "repo": REPO_URL,
            "skills": [path.name for path in installed_targets],
            "verify_exit_code": verify_code,
            "install_exit_code": install_code,
            "output": combined_output,
        },
    )
    if combined_output.strip():
        print(combined_output.strip())
    if verify_code != 0:
        return verify_code
    if install_code == 0:
        _set_installed(True)
    return install_code


def uninstall() -> int:
    run_dir = _run_dir("uninstall")
    repo_path, clone_output = _clone_repo(run_dir)
    if repo_path is None:
        print(clone_output, file=sys.stderr)
        return 1

    source_skills = _find_threejs_skills(repo_path)
    if not source_skills:
        print("No threejs-* skills found in cloned repository.", file=sys.stderr)
        return 1

    removed: list[str] = []
    removed_backup_dir = run_dir / "removed"
    removed_backup_dir.mkdir(parents=True, exist_ok=True)

    for src in source_skills:
        target = USER_SKILLS_DIR / src.name
        if target.is_dir():
            backup_target = removed_backup_dir / src.name
            if backup_target.exists():
                shutil.rmtree(backup_target)
            shutil.copytree(target, backup_target)
            shutil.rmtree(target)
            removed.append(src.name)

    install_code, install_output = _run_command([str(SKILL_INSTALL_BIN)], REPO_ROOT)
    combined_output = clone_output + install_output
    _write_summary(
        run_dir / "uninstall-summary.json",
        {
            "action": "uninstall",
            "repo": REPO_URL,
            "removed": removed,
            "install_exit_code": install_code,
            "output": combined_output,
        },
    )
    if combined_output.strip():
        print(combined_output.strip())
    if install_code == 0:
        _set_installed(False)
    return install_code


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"install", "update", "uninstall"}:
        print("Usage: extension.py install|update|uninstall", file=sys.stderr)
        return 1

    action = argv[1]
    if action == "install":
        return install_or_update("install")
    if action == "update":
        return install_or_update("update")
    return uninstall()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
