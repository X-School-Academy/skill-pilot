import os
import platform
import shlex
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path

from dotenv import dotenv_values

_LOADED_KEYS_ENV = "SAFE_DOTENV_LOADED_KEYS"


def configured_unset_keys() -> list[str]:
    raw = os.environ.get("SAFE_DOTENV_UNSET_KEYS", "")
    keys: list[str] = []
    for key in raw.split(","):
        key = key.strip()
        if key:
            keys.append(key)
    return keys


def loaded_env_key_names() -> list[str]:
    raw = os.environ.get(_LOADED_KEYS_ENV, "")
    names: list[str] = []
    seen: set[str] = set()
    for key in raw.split(","):
        item = key.strip()
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        names.append(item)
    return sorted(names)


def apply_env_key_values(updates: dict[str, str]) -> list[str]:
    applied_keys: list[str] = []
    if not updates:
        return applied_keys

    for key, value in updates.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        os.environ[key] = value
        applied_keys.append(key)

    if applied_keys:
        existing = set(loaded_env_key_names())
        existing.update(applied_keys)
        os.environ[_LOADED_KEYS_ENV] = ",".join(sorted(existing))

    return applied_keys


def safe_env(*, extra: dict[str, str] | None = None, unset_keys: list[str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    to_unset: set[str] = set(unset_keys or [])
    # Internal control vars should not be propagated to child processes.
    to_unset.add("SAFE_DOTENV_UNSET_KEYS")
    to_unset.add("IN_KEYS_SAFE_GUARD")
    for key in to_unset:
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


def read_protected_file(path: str) -> str:
    subprocess.run(
        ["sudo", "-k"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        env=safe_env(),
    )

    try:
        # No shell=True; pass args as a list to avoid injection
        p = subprocess.run(
            ["sudo", "cat", "--", path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            env=safe_env(),
        )
        return p.stdout
    finally:
        subprocess.run(
            ["sudo", "-k"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            env=safe_env(),
        )


def read_protected_file_gui(path: str) -> str:
    system = platform.system()
    if system == "Darwin":
        cmd = f"cat -- {shlex.quote(path)}"
        esc = cmd.replace("\\", "\\\\").replace('"', '\\"')
        script = f'do shell script "{esc}" with administrator privileges'
        proc = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            env=safe_env(),
        )
        return proc.stdout
    if system == "Linux":
        if shutil.which("pkexec") is not None:
            proc = subprocess.run(
                ["pkexec", "cat", "--", path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                env=safe_env(),
            )
            return proc.stdout
        raise RuntimeError("GUI auth requested but pkexec is not available on Linux")
    raise RuntimeError(f"GUI auth requested but unsupported platform: {system}")


def load_env_with_safeguard(path: str | Path, *, override: bool = False, require_gui_auth: bool = False) -> bool:
    if os.getenv("IN_KEYS_SAFE_GUARD", "").strip() == "1" and configured_unset_keys():
        print("[safe_dotenv] IN_KEYS_SAFE_GUARD=1 with preloaded env detected; skip loading .env again.", file=sys.stderr)
        return False

    env_path = Path(path).resolve()
    if not env_path.exists():
        print(f"[safe_dotenv] Env file not found: {env_path}", file=sys.stderr)
        return False

    if require_gui_auth:
        print(
            f"[safe_dotenv] GUI auth requested for protected read of {env_path}.",
            file=sys.stderr,
        )
        try:
            raw = read_protected_file_gui(str(env_path))
        except Exception as exc:
            print(f"[safe_dotenv] GUI-protected read failed: {exc}", file=sys.stderr)
            return False
    elif os.access(env_path, os.R_OK):
        print(
            "[safe_dotenv] Warning: your .env file not protected by safe guard. "
            "To enable it run: core/bin/keys-safe-guard",
            file=sys.stderr,
        )
        raw = env_path.read_text(encoding="utf-8")
    else:
        print(
            f"[safe_dotenv] No direct read permission for {env_path}. "
            "Attempting protected read with sudo.",
            file=sys.stderr,
        )
        print(
            "[safe_dotenv] Next step if this fails: run core/bin/keys-safe-guard, "
            "then ensure your user can run sudo for protected env reads.",
            file=sys.stderr,
        )
        try:
            raw = read_protected_file(str(env_path))
        except subprocess.CalledProcessError as exc:
            err = (exc.stderr or "").strip() or str(exc)
            print(f"[safe_dotenv] Protected read failed: {err}", file=sys.stderr)
            return False

    values = dotenv_values(stream=StringIO(raw))
    loaded = False
    updates: dict[str, str] = {}
    for key, val in values.items():
        if not isinstance(key, str) or not isinstance(val, str):
            continue
        if override or key not in os.environ:
            updates[key] = val

    applied_keys = apply_env_key_values(updates)
    loaded = bool(applied_keys)

    return loaded
