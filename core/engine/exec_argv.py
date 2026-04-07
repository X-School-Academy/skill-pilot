import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


_child_proc: subprocess.Popen[str] | None = None


def _forward_signal(sig: int) -> bool:
    proc = _child_proc
    if proc is None:
        return False
    try:
        os.killpg(proc.pid, sig)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        try:
            proc.send_signal(sig)
            return True
        except ProcessLookupError:
            return False


def _forward_and_wait(sig: int) -> None:
    proc = _child_proc
    if proc is None:
        raise SystemExit(128 + sig)
    if not _forward_signal(sig):
        raise SystemExit(128 + sig)
    deadline = time.monotonic() + 1.5
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise SystemExit(proc.returncode or (128 + sig))
        time.sleep(0.05)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    raise SystemExit(128 + sig)


def _install_signal_handlers() -> None:
    def _handler(sig: int, _frame: object) -> None:
        _forward_and_wait(sig)

    def _passthrough(sig: int, _frame: object) -> None:
        _forward_signal(sig)

    for handled in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(handled, _handler)
    signal.signal(signal.SIGWINCH, _passthrough)


def main() -> int:
    global _child_proc
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

    _install_signal_handlers()
    _child_proc = subprocess.Popen(
        argv,
        env=env,
        start_new_session=True,
        text=True,
    )
    try:
        return _child_proc.wait()
    finally:
        if _child_proc is not None and _child_proc.poll() is None:
            try:
                os.killpg(_child_proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                try:
                    _child_proc.terminate()
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
