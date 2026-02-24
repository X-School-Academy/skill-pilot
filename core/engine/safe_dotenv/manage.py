#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _parse_key_values(items: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"invalid key/value '{item}', expected KEY=VALUE")
        key, value = item.split("=", 1)
        key = key.strip()
        if not _KEY_RE.fullmatch(key):
            raise ValueError(f"invalid key '{key}'")
        parsed.append((key, value))
    return parsed


def _upsert_key_values(text: str, updates: list[tuple[str, str]]) -> str:
    lines = text.splitlines()
    key_to_value = {k: v for k, v in updates}
    remaining = set(key_to_value.keys())
    updated_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated_lines.append(line)
            continue
        key, _ = line.split("=", 1)
        key = key.strip()
        if key in key_to_value:
            updated_lines.append(f"{key}={key_to_value[key]}")
            remaining.discard(key)
        else:
            updated_lines.append(line)

    for key in updates:
        if key[0] in remaining:
            updated_lines.append(f"{key[0]}={key[1]}")

    return "\n".join(updated_lines).rstrip("\n") + "\n"


def _remove_key(text: str, target_key: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            out.append(line)
            continue
        key, _ = line.split("=", 1)
        if key.strip() == target_key:
            continue
        out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _cmd_put(args: argparse.Namespace) -> int:
    env_file = Path(args.env_file).resolve()
    updates = _parse_key_values(args.key_values)
    text = _read_text(env_file)
    updated = _upsert_key_values(text, updates)
    _write_text(env_file, updated)
    print(f"Updated {len(updates)} key(s) in {env_file}")
    return 0


def _cmd_disable(args: argparse.Namespace) -> int:
    env_file = Path(args.env_file).resolve()
    text = _read_text(env_file)
    updated = _remove_key(text, "IN_KEYS_SAFE_GUARD")
    _write_text(env_file, updated)
    print(f"Removed IN_KEYS_SAFE_GUARD from {env_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage config/.env key updates")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_put = sub.add_parser("put", help="Update or insert one or more KEY=VALUE pairs")
    p_put.add_argument("--env-file", required=True)
    p_put.add_argument("key_values", nargs="+")
    p_put.set_defaults(func=_cmd_put)

    p_disable = sub.add_parser("disable", help="Remove IN_KEYS_SAFE_GUARD flag from env file")
    p_disable.add_argument("--env-file", required=True)
    p_disable.set_defaults(func=_cmd_disable)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
