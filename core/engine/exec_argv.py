import json
import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: exec_argv.py <payload.json>", file=sys.stderr)
        return 2

    payload_path = Path(sys.argv[1]).expanduser().resolve()
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    argv = payload.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
        raise ValueError("payload argv must be a non-empty string list")

    raw_env = payload.get("env") or {}
    if not isinstance(raw_env, dict):
        raise ValueError("payload env must be an object when provided")

    env = os.environ.copy()
    for key, value in raw_env.items():
        env[str(key)] = str(value)

    try:
        payload_path.unlink()
    except OSError:
        pass

    os.execvpe(argv[0], argv, env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
