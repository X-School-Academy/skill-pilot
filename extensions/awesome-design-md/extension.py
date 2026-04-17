"""Awesome Design MD extension installer.

install  – clone the repo into src/ without git history
update   – pull latest changes into src/
uninstall – remove src/
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/X-School-Academy/extension-awesome-design-md.git"
EXT_DIR = Path(__file__).resolve().parent
EXTENSION_JSON5 = EXT_DIR / "extension.json5"
SRC_DIR = EXT_DIR / "src"


def _set_installed(value: bool) -> None:
    """Update the ``installed`` field in extension.json5."""
    if not EXTENSION_JSON5.is_file():
        return
    text = EXTENSION_JSON5.read_text(encoding="utf-8")
    if re.search(r"installed\s*:", text):
        text = re.sub(r"(installed\s*:\s*)(true|false)", rf"\g<1>{'true' if value else 'false'}", text)
    else:
        text = re.sub(r"(\s*)\}", rf"\1  installed: {'true' if value else 'false'},\n\1}}", text)
    EXTENSION_JSON5.write_text(text, encoding="utf-8")


def install() -> int:
    if SRC_DIR.exists():
        print(f"src/ already exists at {SRC_DIR}. Use 'update' instead.")
        return 1

    print(f"Cloning {REPO_URL} into {SRC_DIR} (without git history)...")
    tmp_clone = EXT_DIR / "_tmp_clone"
    if tmp_clone.exists():
        shutil.rmtree(tmp_clone)

    result = subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, str(tmp_clone)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"git clone failed:\n{result.stderr}", file=sys.stderr)
        if tmp_clone.exists():
            shutil.rmtree(tmp_clone)
        return 1

    # Remove .git to strip history
    git_dir = tmp_clone / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    tmp_clone.rename(SRC_DIR)
    _set_installed(True)
    print("Install complete.")
    return 0


def update() -> int:
    if not SRC_DIR.exists():
        print("src/ does not exist. Run 'install' first.")
        return 1

    print(f"Updating {SRC_DIR} from {REPO_URL}...")
    tmp_clone = EXT_DIR / "_tmp_clone"
    if tmp_clone.exists():
        shutil.rmtree(tmp_clone)

    result = subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, str(tmp_clone)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"git clone failed:\n{result.stderr}", file=sys.stderr)
        if tmp_clone.exists():
            shutil.rmtree(tmp_clone)
        return 1

    git_dir = tmp_clone / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    shutil.rmtree(SRC_DIR)
    tmp_clone.rename(SRC_DIR)
    _set_installed(True)
    print("Update complete.")
    return 0


def uninstall() -> int:
    if not SRC_DIR.exists():
        print("src/ does not exist. Nothing to uninstall.")
        return 0

    print(f"Removing {SRC_DIR}...")
    shutil.rmtree(SRC_DIR)
    _set_installed(False)
    print("Uninstall complete.")
    return 0


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "install":
        return install()
    if action == "update":
        return update()
    if action == "uninstall":
        return uninstall()
    print("Usage: extension.py [install|update|uninstall]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
