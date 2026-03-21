from __future__ import annotations

import os
import pty
import re
import select
import shlex
import signal
import struct
import subprocess
import threading
import time
import uuid
from collections import deque
from fcntl import ioctl
from termios import TIOCSWINSZ
from typing import Callable

from constants import TMUX_SPECIAL_KEYS
from helpers import (
    _build_command,
    _has_tty_error,
    _is_interactive_command,
    _normalize_lifecycle,
    _normalize_transport,
)
from ssh import SSHClientPool
from terminal import TerminalState

_TMUX_CAPTURE_BOUND_RE = re.compile(r"^-?\d+$|^-$")


def _normalize_tmux_capture_bound(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if not _TMUX_CAPTURE_BOUND_RE.fullmatch(normalized):
        raise ValueError(f"{name} must be '-', or an integer string like '-200' or '0'")
    return normalized


class SessionBase:
    transport: str
    lifecycle: str
    target: str


class LocalPtySession(SessionBase):
    transport = "pty"
    lifecycle = "direct"
    target = "local"

    def __init__(
        self,
        command: str,
        args: list[str] | None,
        cwd: str | None,
        env: dict[str, str] | None,
        cols: int,
        rows: int,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.command = command
        self.created_at = time.time()
        self.cols = cols
        self.rows = rows
        self.exit_code: int | None = None
        self._alive = True
        self._lock = threading.RLock()
        self._ansi_log = deque(maxlen=10000)

        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd
        self._slave_fd = slave_fd
        self._set_winsize(cols, rows)
        os.set_blocking(self._master_fd, False)

        full_env = dict(os.environ)
        if env:
            full_env.update(env)

        argv = [command, *(args or [])]
        try:
            self._proc = subprocess.Popen(
                argv,
                stdin=self._slave_fd,
                stdout=self._slave_fd,
                stderr=self._slave_fd,
                cwd=cwd or os.getcwd(),
                env=full_env,
                start_new_session=True,
                close_fds=True,
            )
        except Exception:
            os.close(self._master_fd)
            os.close(self._slave_fd)
            raise
        finally:
            try:
                os.close(self._slave_fd)
            except OSError:
                pass

        self._terminal = TerminalState(cols, rows, self._write_raw)
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._waiter = threading.Thread(target=self._wait_loop, daemon=True)
        self._waiter.start()

    def _set_winsize(self, cols: int, rows: int) -> None:
        buf = struct.pack("HHHH", rows, cols, 0, 0)
        ioctl(self._master_fd, TIOCSWINSZ, buf)

    def _write_raw(self, data: str) -> None:
        if not self._alive:
            return
        try:
            os.write(self._master_fd, data.encode("utf-8", errors="ignore"))
        except OSError:
            pass

    def _read_loop(self) -> None:
        while self._alive:
            try:
                ready, _, _ = select.select([self._master_fd], [], [], 0.1)
            except (OSError, ValueError):
                break
            if not ready:
                continue
            try:
                data = os.read(self._master_fd, 65536)
            except BlockingIOError:
                continue
            except OSError:
                break
            if not data:
                continue
            text = data.decode("utf-8", errors="replace")
            with self._lock:
                self._ansi_log.append(text)
                self._terminal.feed(text)

    def _wait_loop(self) -> None:
        try:
            self.exit_code = self._proc.wait()
        finally:
            self._alive = False

    @property
    def pid(self) -> int:
        return self._proc.pid

    @property
    def is_alive(self) -> bool:
        return self._alive and self._proc.poll() is None

    @property
    def size(self) -> dict[str, int]:
        return {"cols": self.cols, "rows": self.rows}

    def write(self, data: str) -> None:
        if not self.is_alive:
            raise RuntimeError("Session is no longer alive")
        self._write_raw(data)

    def resize(self, cols: int, rows: int) -> dict[str, int]:
        prev = {"cols": self.cols, "rows": self.rows}
        self.cols = cols
        self.rows = rows
        self._set_winsize(cols, rows)
        with self._lock:
            self._terminal.resize(cols, rows)
        return prev

    def _format_screen(self, lines: list[str]) -> str:
        line_num_width = len(str(max(1, len(lines))))
        separator = "-" * (self.cols + line_num_width + 3)
        body = []
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(line_num_width)
            padded = line[: self.cols].ljust(self.cols)
            body.append(f"{line_num} |{padded}|")
        return "\n".join([separator, *body, separator])

    def get_snapshot(
        self,
        include_scrollback: bool = False,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> dict:
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        with self._lock:
            snap = self._terminal.snapshot(include_scrollback)
        return {
            "text": self._format_screen(snap["lines"]),
            "cursorPosition": snap["cursorPosition"],
            "terminalSize": snap["terminalSize"],
            "activeBuffer": snap["activeBuffer"],
            "processTitle": self.command,
        }

    def get_ansi_snapshot(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        with self._lock:
            return "".join(self._ansi_log)

    def get_raw_output(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        return self.get_ansi_snapshot()

    def close(self, sig: str = "SIGTERM") -> dict[str, int | None]:
        sig_value = getattr(signal, sig, signal.SIGTERM)
        if self.is_alive:
            try:
                os.killpg(self._proc.pid, sig_value)
            except ProcessLookupError:
                pass
        try:
            self._proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self._proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                self._proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass
        self._alive = False
        try:
            os.close(self._master_fd)
        except OSError:
            pass
        return {"exitCode": self.exit_code, "signal": None}


class LocalPipeSession(SessionBase):
    transport = "pipe"
    lifecycle = "direct"
    target = "local"

    def __init__(
        self,
        command: str,
        args: list[str] | None,
        cwd: str | None,
        env: dict[str, str] | None,
        cols: int,
        rows: int,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.command = command
        self.created_at = time.time()
        self.cols = cols
        self.rows = rows
        self.exit_code: int | None = None
        self._alive = True
        self._lock = threading.RLock()
        self._stdout_log = deque(maxlen=5000)
        self._stderr_log = deque(maxlen=5000)
        self._ansi_log = deque(maxlen=10000)

        full_env = dict(os.environ)
        if env:
            full_env.update(env)

        argv = [command, *(args or [])]
        self._proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd or os.getcwd(),
            env=full_env,
            start_new_session=True,
            close_fds=True,
        )
        self._stdout_reader = threading.Thread(
            target=self._read_pipe,
            args=(self._proc.stdout, self._stdout_log),
            daemon=True,
        )
        self._stderr_reader = threading.Thread(
            target=self._read_pipe,
            args=(self._proc.stderr, self._stderr_log),
            daemon=True,
        )
        self._stdout_reader.start()
        self._stderr_reader.start()
        self._waiter = threading.Thread(target=self._wait_loop, daemon=True)
        self._waiter.start()

    def _read_pipe(self, stream, buf: deque[str]) -> None:
        if stream is None:
            return
        while self._alive:
            try:
                chunk = stream.read(4096)
            except Exception:
                break
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            with self._lock:
                buf.append(text)
                self._ansi_log.append(text)

    def _wait_loop(self) -> None:
        try:
            self.exit_code = self._proc.wait()
        finally:
            self._alive = False

    @property
    def pid(self) -> int:
        return self._proc.pid

    @property
    def is_alive(self) -> bool:
        return self._alive and self._proc.poll() is None

    @property
    def size(self) -> dict[str, int]:
        return {"cols": self.cols, "rows": self.rows}

    def write(self, data: str) -> None:
        if not self.is_alive:
            raise RuntimeError("Session is no longer alive")
        if self._proc.stdin is None:
            raise RuntimeError("stdin unavailable")
        self._proc.stdin.write(data.encode("utf-8", errors="ignore"))
        self._proc.stdin.flush()

    def resize(self, cols: int, rows: int) -> dict[str, int]:
        prev = {"cols": self.cols, "rows": self.rows}
        self.cols = cols
        self.rows = rows
        return prev

    def _joined_output(self) -> str:
        with self._lock:
            stdout = "".join(self._stdout_log)
            stderr = "".join(self._stderr_log)
        return stdout + stderr

    def _format_screen(self, text: str) -> str:
        lines = text.splitlines() or [""]
        line_num_width = len(str(max(1, len(lines))))
        separator = "-" * (self.cols + line_num_width + 3)
        body = []
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(line_num_width)
            padded = line[: self.cols].ljust(self.cols)
            body.append(f"{line_num} |{padded}|")
        return "\n".join([separator, *body, separator])

    def get_snapshot(
        self,
        include_scrollback: bool = False,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> dict:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        text = self._joined_output()
        with self._lock:
            stdout = "".join(self._stdout_log)
            stderr = "".join(self._stderr_log)
        return {
            "text": self._format_screen(text),
            "cursorPosition": {"x": 0, "y": 0},
            "terminalSize": {"cols": self.cols, "rows": self.rows},
            "activeBuffer": "normal",
            "processTitle": self.command,
            "stdout": stdout,
            "stderr": stderr,
        }

    def get_ansi_snapshot(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        with self._lock:
            return "".join(self._ansi_log)

    def get_raw_output(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        return self._joined_output()

    def close(self, sig: str = "SIGTERM") -> dict[str, int | None]:
        sig_value = getattr(signal, sig, signal.SIGTERM)
        if self.is_alive:
            try:
                os.killpg(self._proc.pid, sig_value)
            except ProcessLookupError:
                pass
        try:
            self._proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self._proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self._alive = False
        for stream in (self._proc.stdin, self._proc.stdout, self._proc.stderr):
            if stream is None:
                continue
            try:
                stream.close()
            except Exception:
                pass
        return {"exitCode": self.exit_code, "signal": None}


class SSHPtySession(SessionBase):
    transport = "pty"
    lifecycle = "direct"

    def __init__(
        self,
        pool: SSHClientPool,
        profile: str,
        command: str,
        args: list[str] | None,
        cwd: str | None,
        env: dict[str, str] | None,
        cols: int,
        rows: int,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.target = f"ssh:{profile}"
        self.command = command
        self.created_at = time.time()
        self.cols = cols
        self.rows = rows
        self.exit_code: int | None = None
        self._alive = True
        self._lock = threading.RLock()
        self._ansi_log = deque(maxlen=10000)

        client = pool.get_client(profile)
        transport = client.get_transport()
        if transport is None or not transport.is_active():
            raise RuntimeError(f"SSH transport unavailable for profile {profile}")

        self._chan = transport.open_session()
        self._chan.get_pty(term="xterm", width=cols, height=rows)
        cmd = _build_command(command, args, cwd, env)
        self._chan.exec_command(cmd)

        self._terminal = TerminalState(cols, rows, self._write_raw)
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._waiter = threading.Thread(target=self._wait_loop, daemon=True)
        self._waiter.start()

    def _write_raw(self, data: str) -> None:
        if not self._alive:
            return
        try:
            self._chan.send(data)
        except Exception:
            pass

    def _read_loop(self) -> None:
        while self._alive:
            try:
                if self._chan.recv_ready():
                    data = self._chan.recv(65536)
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace")
                    with self._lock:
                        self._ansi_log.append(text)
                        self._terminal.feed(text)
                else:
                    time.sleep(0.05)
            except Exception:
                break

    def _wait_loop(self) -> None:
        while self._alive:
            try:
                if self._chan.exit_status_ready():
                    self.exit_code = self._chan.recv_exit_status()
                    self._alive = False
                    return
            except Exception:
                self._alive = False
                return
            time.sleep(0.05)

    @property
    def pid(self) -> int:
        return -1

    @property
    def is_alive(self) -> bool:
        return self._alive and not self._chan.exit_status_ready()

    @property
    def size(self) -> dict[str, int]:
        return {"cols": self.cols, "rows": self.rows}

    def write(self, data: str) -> None:
        if not self.is_alive:
            raise RuntimeError("Session is no longer alive")
        self._write_raw(data)

    def resize(self, cols: int, rows: int) -> dict[str, int]:
        prev = {"cols": self.cols, "rows": self.rows}
        self.cols = cols
        self.rows = rows
        try:
            self._chan.resize_pty(width=cols, height=rows)
        except Exception:
            pass
        with self._lock:
            self._terminal.resize(cols, rows)
        return prev

    def _format_screen(self, lines: list[str]) -> str:
        line_num_width = len(str(max(1, len(lines))))
        separator = "-" * (self.cols + line_num_width + 3)
        body = []
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(line_num_width)
            padded = line[: self.cols].ljust(self.cols)
            body.append(f"{line_num} |{padded}|")
        return "\n".join([separator, *body, separator])

    def get_snapshot(
        self,
        include_scrollback: bool = False,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> dict:
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        with self._lock:
            snap = self._terminal.snapshot(include_scrollback)
        return {
            "text": self._format_screen(snap["lines"]),
            "cursorPosition": snap["cursorPosition"],
            "terminalSize": snap["terminalSize"],
            "activeBuffer": snap["activeBuffer"],
            "processTitle": self.command,
        }

    def get_ansi_snapshot(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        with self._lock:
            return "".join(self._ansi_log)

    def get_raw_output(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        return self.get_ansi_snapshot()

    def close(self, sig: str = "SIGTERM") -> dict[str, int | None]:
        _ = sig
        try:
            self._chan.close()
        except Exception:
            pass
        self._alive = False
        return {"exitCode": self.exit_code, "signal": None}


class SSHPipeSession(SessionBase):
    transport = "pipe"
    lifecycle = "direct"

    def __init__(
        self,
        pool: SSHClientPool,
        profile: str,
        command: str,
        args: list[str] | None,
        cwd: str | None,
        env: dict[str, str] | None,
        cols: int,
        rows: int,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.target = f"ssh:{profile}"
        self.command = command
        self.created_at = time.time()
        self.cols = cols
        self.rows = rows
        self.exit_code: int | None = None
        self._alive = True
        self._lock = threading.RLock()
        self._stdout_log = deque(maxlen=5000)
        self._stderr_log = deque(maxlen=5000)
        self._ansi_log = deque(maxlen=10000)

        client = pool.get_client(profile)
        cmd = _build_command(command, args, cwd, env)
        stdin_f, stdout_f, stderr_f = client.exec_command(cmd, get_pty=False)
        self._stdin = stdin_f
        self._stdout = stdout_f
        self._stderr = stderr_f
        self._chan = stdout_f.channel

        self._stdout_reader = threading.Thread(target=self._read_stream, args=(self._stdout, self._stdout_log), daemon=True)
        self._stderr_reader = threading.Thread(target=self._read_stream, args=(self._stderr, self._stderr_log), daemon=True)
        self._stdout_reader.start()
        self._stderr_reader.start()
        self._waiter = threading.Thread(target=self._wait_loop, daemon=True)
        self._waiter.start()

    def _read_stream(self, stream, buf: deque[str]) -> None:
        while self._alive:
            try:
                chunk = stream.read(4096)
            except Exception:
                break
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            with self._lock:
                buf.append(text)
                self._ansi_log.append(text)

    def _wait_loop(self) -> None:
        while self._alive:
            try:
                if self._chan.exit_status_ready():
                    self.exit_code = self._chan.recv_exit_status()
                    self._alive = False
                    return
            except Exception:
                self._alive = False
                return
            time.sleep(0.05)

    @property
    def pid(self) -> int:
        return -1

    @property
    def is_alive(self) -> bool:
        return self._alive and not self._chan.exit_status_ready()

    @property
    def size(self) -> dict[str, int]:
        return {"cols": self.cols, "rows": self.rows}

    def write(self, data: str) -> None:
        if not self.is_alive:
            raise RuntimeError("Session is no longer alive")
        self._stdin.write(data)
        self._stdin.flush()

    def resize(self, cols: int, rows: int) -> dict[str, int]:
        prev = {"cols": self.cols, "rows": self.rows}
        self.cols = cols
        self.rows = rows
        return prev

    def _joined_output(self) -> str:
        with self._lock:
            stdout = "".join(self._stdout_log)
            stderr = "".join(self._stderr_log)
        return stdout + stderr

    def _format_screen(self, text: str) -> str:
        lines = text.splitlines() or [""]
        line_num_width = len(str(max(1, len(lines))))
        separator = "-" * (self.cols + line_num_width + 3)
        body = []
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(line_num_width)
            padded = line[: self.cols].ljust(self.cols)
            body.append(f"{line_num} |{padded}|")
        return "\n".join([separator, *body, separator])

    def get_snapshot(
        self,
        include_scrollback: bool = False,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> dict:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        text = self._joined_output()
        with self._lock:
            stdout = "".join(self._stdout_log)
            stderr = "".join(self._stderr_log)
        return {
            "text": self._format_screen(text),
            "cursorPosition": {"x": 0, "y": 0},
            "terminalSize": {"cols": self.cols, "rows": self.rows},
            "activeBuffer": "normal",
            "processTitle": self.command,
            "stdout": stdout,
            "stderr": stderr,
        }

    def get_ansi_snapshot(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        with self._lock:
            return "".join(self._ansi_log)

    def get_raw_output(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        _ = include_scrollback
        _ = join_wrapped_lines
        _ = capture_start
        _ = capture_end
        return self._joined_output()

    def close(self, sig: str = "SIGTERM") -> dict[str, int | None]:
        _ = sig
        try:
            self._chan.close()
        except Exception:
            pass
        for f in (self._stdin, self._stdout, self._stderr):
            try:
                f.close()
            except Exception:
                pass
        self._alive = False
        return {"exitCode": self.exit_code, "signal": None}


class TmuxSession(SessionBase):
    transport = "pty"
    lifecycle = "tmux"

    def __init__(
        self,
        target: str,
        runner: Callable[[str], tuple[str, str, int]],
        command: str,
        args: list[str] | None,
        cwd: str | None,
        env: dict[str, str] | None,
        cols: int,
        rows: int,
        tmux_session_name: str | None = None,
        tmux_pane_ref: str | None = None,
        create_new: bool = True,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.target = target
        self.command = command
        self.created_at = time.time()
        self.cols = cols
        self.rows = rows
        self.exit_code: int | None = None
        self._runner = runner
        self._name = tmux_session_name or f"mcp-{self.id[:12]}"
        self._pane = tmux_pane_ref or f"{self._name}:0.0"

        if create_new:
            cmd = _build_command(command, args, cwd, env)
            tmux_cmd = (
                f"tmux new-session -d -s {shlex.quote(self._name)} "
                f"-x {cols} -y {rows} {shlex.quote(cmd)}"
            )
            out, err, code = self._runner(tmux_cmd)
            if code != 0:
                raise RuntimeError(f"failed to create tmux session: {(out + err).strip()}")
        else:
            if tmux_pane_ref:
                out, err, code = self._runner(
                    f"tmux display-message -p -t {shlex.quote(tmux_pane_ref)} '#{{session_name}}'"
                )
                if code != 0:
                    raise RuntimeError((out + err).strip() or f"tmux pane not found: {tmux_pane_ref}")
                resolved_name = out.strip()
                if not resolved_name:
                    raise RuntimeError(f"unable to resolve session for pane: {tmux_pane_ref}")
                self._name = resolved_name
                self._pane = tmux_pane_ref
            else:
                out, err, code = self._runner(f"tmux has-session -t {shlex.quote(self._name)}")
                if code != 0:
                    raise RuntimeError((out + err).strip() or f"tmux session not found: {self._name}")

    @property
    def pid(self) -> int:
        return -1

    @property
    def is_alive(self) -> bool:
        _, _, code = self._runner(f"tmux has-session -t {shlex.quote(self._name)}")
        return code == 0

    @property
    def size(self) -> dict[str, int]:
        return {"cols": self.cols, "rows": self.rows}

    def _capture(
        self,
        include_scrollback: bool,
        include_ansi: bool = False,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        start_value = _normalize_tmux_capture_bound(capture_start, "capture_start")
        end_value = _normalize_tmux_capture_bound(capture_end, "capture_end")
        if start_value is None and include_scrollback:
            start_value = "-"
        ansi_flag = "-e" if include_ansi else ""
        join_flag = "-J" if join_wrapped_lines else ""
        start_flag = f"-S {shlex.quote(start_value)}" if start_value is not None else ""
        end_flag = f"-E {shlex.quote(end_value)}" if end_value is not None else ""
        out, err, code = self._runner(
            f"tmux capture-pane -p {join_flag} {ansi_flag} {start_flag} {end_flag} -t {shlex.quote(self._pane)}"
        )
        if code != 0:
            raise RuntimeError((out + err).strip() or "tmux capture failed")
        return out

    def _format_screen(self, text: str) -> str:
        lines = text.splitlines() or [""]
        line_num_width = len(str(max(1, len(lines))))
        separator = "-" * (self.cols + line_num_width + 3)
        body = []
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(line_num_width)
            padded = line[: self.cols].ljust(self.cols)
            body.append(f"{line_num} |{padded}|")
        return "\n".join([separator, *body, separator])

    def write(self, data: str) -> None:
        if not self.is_alive:
            raise RuntimeError("Session is no longer alive")
        text = data.replace("\r", "")
        out, err, code = self._runner(f"tmux send-keys -t {shlex.quote(self._pane)} -l {shlex.quote(text)}")
        if code != 0:
            raise RuntimeError((out + err).strip() or "tmux send-keys failed")

    def send_special(self, key: str) -> None:
        if not self.is_alive:
            raise RuntimeError("Session is no longer alive")
        key_name = TMUX_SPECIAL_KEYS.get(key.lower())
        if key_name is None:
            raise ValueError(f"Unsupported specialKey for tmux: {key}")
        out, err, code = self._runner(f"tmux send-keys -t {shlex.quote(self._pane)} {shlex.quote(key_name)}")
        if code != 0:
            raise RuntimeError((out + err).strip() or "tmux send-keys failed")

    def resize(self, cols: int, rows: int) -> dict[str, int]:
        prev = {"cols": self.cols, "rows": self.rows}
        out, err, code = self._runner(
            f"tmux resize-window -t {shlex.quote(self._name)} -x {cols} -y {rows}"
        )
        if code != 0:
            raise RuntimeError((out + err).strip() or "tmux resize failed")
        self.cols = cols
        self.rows = rows
        return prev

    def get_snapshot(
        self,
        include_scrollback: bool = False,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> dict:
        text = self._capture(
            include_scrollback,
            join_wrapped_lines=join_wrapped_lines,
            capture_start=capture_start,
            capture_end=capture_end,
        )
        return {
            "text": self._format_screen(text),
            "cursorPosition": {"x": 0, "y": 0},
            "terminalSize": {"cols": self.cols, "rows": self.rows},
            "activeBuffer": "normal",
            "processTitle": self.command,
            "tmuxSession": self._name,
            "tmuxPane": self._pane,
        }

    def get_ansi_snapshot(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        return self._capture(
            include_scrollback=include_scrollback,
            include_ansi=True,
            join_wrapped_lines=join_wrapped_lines,
            capture_start=capture_start,
            capture_end=capture_end,
        )

    def get_raw_output(
        self,
        include_scrollback: bool = True,
        join_wrapped_lines: bool = True,
        capture_start: str | None = None,
        capture_end: str | None = None,
    ) -> str:
        return self._capture(
            include_scrollback=include_scrollback,
            join_wrapped_lines=join_wrapped_lines,
            capture_start=capture_start,
            capture_end=capture_end,
        )

    def close(self, sig: str = "SIGTERM") -> dict[str, int | None]:
        if sig == "DETACH":
            return {"exitCode": self.exit_code, "signal": None}
        self._runner(f"tmux kill-session -t {shlex.quote(self._name)}")
        return {"exitCode": self.exit_code, "signal": None}


class SessionManager:
    def __init__(self, ssh_pool: SSHClientPool, max_sessions: int = 20) -> None:
        self._sessions: dict[str, SessionBase] = {}
        self._max_sessions = max_sessions
        self._ssh_pool = ssh_pool
        self._lock = threading.RLock()

    def _run_local(self, command: str) -> tuple[str, str, int]:
        proc = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True,
        )
        return proc.stdout, proc.stderr, proc.returncode

    def _run_remote(self, profile: str, command: str) -> tuple[str, str, int]:
        client = self._ssh_pool.get_client(profile)
        stdin_f, stdout_f, stderr_f = client.exec_command(command, get_pty=False)
        _ = stdin_f
        stdout = stdout_f.read().decode("utf-8", errors="replace")
        stderr = stderr_f.read().decode("utf-8", errors="replace")
        code = stdout_f.channel.recv_exit_status()
        return stdout, stderr, code

    def _tmux_runner_for_target(self, target: str) -> Callable[[str], tuple[str, str, int]]:
        if target == "local":
            return self._run_local
        if target.startswith("ssh:"):
            profile = target.split(":", 1)[1]
            self._ssh_pool.get_profile(profile)
            return lambda cmd, p=profile: self._run_remote(p, cmd)
        raise ValueError("target must be local or ssh:<profile>")

    def create(
        self,
        *,
        target: str,
        command: str,
        args: list[str] | None,
        cwd: str | None,
        env: dict[str, str] | None,
        transport: str,
        lifecycle: str,
        cols: int,
        rows: int,
    ) -> SessionBase:
        with self._lock:
            if len(self._sessions) >= self._max_sessions:
                self._cleanup_dead_sessions()
                if len(self._sessions) >= self._max_sessions:
                    raise RuntimeError(f"Maximum sessions ({self._max_sessions}) reached")

            transport = _normalize_transport(transport)
            lifecycle = _normalize_lifecycle(lifecycle)
            if lifecycle == "tmux":
                runner = self._tmux_runner_for_target(target)
                session = TmuxSession(target, runner, command, args, cwd, env, cols, rows)
            elif target == "local":
                session = self._create_local_direct(command, args, cwd, env, transport, cols, rows)
            elif target.startswith("ssh:"):
                profile = target.split(":", 1)[1]
                self._ssh_pool.get_profile(profile)
                session = self._create_ssh_direct(profile, command, args, cwd, env, transport, cols, rows)
            else:
                raise ValueError("target must be local or ssh:<profile>")

            self._sessions[session.id] = session
            return session

    def attach_tmux(
        self,
        target: str,
        tmux_session_name: str | None,
        tmux_pane_ref: str | None,
        cols: int,
        rows: int,
    ) -> SessionBase:
        with self._lock:
            if len(self._sessions) >= self._max_sessions:
                self._cleanup_dead_sessions()
                if len(self._sessions) >= self._max_sessions:
                    raise RuntimeError(f"Maximum sessions ({self._max_sessions}) reached")
            runner = self._tmux_runner_for_target(target)
            session = TmuxSession(
                target=target,
                runner=runner,
                command=f"attach:{tmux_pane_ref or tmux_session_name}",
                args=None,
                cwd=None,
                env=None,
                cols=cols,
                rows=rows,
                tmux_session_name=tmux_session_name,
                tmux_pane_ref=tmux_pane_ref,
                create_new=False,
            )
            self._sessions[session.id] = session
            return session

    def list_tmux(self, target: str) -> list[dict]:
        runner = self._tmux_runner_for_target(target)
        format_str = "#{session_name}||#{session_id}||#{?session_attached,1,0}||#{session_windows}"
        out, err, code = runner(f"tmux list-sessions -F {shlex.quote(format_str)}")
        if code != 0:
            text = (out + err).strip()
            if "no server running" in text.lower():
                return []
            raise RuntimeError(text or "failed to list tmux sessions")
        sessions: list[dict] = []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("||")
            if len(parts) != 4:
                continue
            name, sid, attached, windows = parts
            sessions.append(
                {
                    "name": name,
                    "id": sid,
                    "attached": attached == "1",
                    "windows": int(windows),
                }
            )
        return sessions

    def _create_local_direct(self, command, args, cwd, env, transport, cols, rows):
        if transport == "pty":
            return LocalPtySession(command, args, cwd, env, cols, rows)
        if transport == "pipe":
            return LocalPipeSession(command, args, cwd, env, cols, rows)
        if _is_interactive_command(command, args):
            return LocalPtySession(command, args, cwd, env, cols, rows)
        pipe = LocalPipeSession(command, args, cwd, env, cols, rows)
        time.sleep(0.1)
        if (not pipe.is_alive) and _has_tty_error(pipe.get_raw_output()):
            pipe.close("SIGTERM")
            return LocalPtySession(command, args, cwd, env, cols, rows)
        return pipe

    def _create_ssh_direct(self, profile, command, args, cwd, env, transport, cols, rows):
        if transport == "pty":
            return SSHPtySession(self._ssh_pool, profile, command, args, cwd, env, cols, rows)
        if transport == "pipe":
            return SSHPipeSession(self._ssh_pool, profile, command, args, cwd, env, cols, rows)
        if _is_interactive_command(command, args):
            return SSHPtySession(self._ssh_pool, profile, command, args, cwd, env, cols, rows)
        pipe = SSHPipeSession(self._ssh_pool, profile, command, args, cwd, env, cols, rows)
        time.sleep(0.15)
        if (not pipe.is_alive) and _has_tty_error(pipe.get_raw_output()):
            pipe.close("SIGTERM")
            return SSHPtySession(self._ssh_pool, profile, command, args, cwd, env, cols, rows)
        return pipe

    def get_or_throw(self, session_id: str) -> SessionBase:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise RuntimeError(f"Session not found: {session_id}")
            return session

    def list(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "sessionId": s.id,
                    "target": s.target,
                    "command": getattr(s, "command", ""),
                    "pid": s.pid,
                    "cols": s.size["cols"],
                    "rows": s.size["rows"],
                    "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s.created_at)),
                    "isAlive": s.is_alive,
                    "transport": s.transport,
                    "lifecycle": s.lifecycle,
                }
                for s in self._sessions.values()
            ]

    def terminate(self, session_id: str, sig: str = "SIGTERM") -> dict[str, int | None]:
        with self._lock:
            session = self.get_or_throw(session_id)
            result = session.close(sig)
            self._sessions.pop(session_id, None)
            return result

    def detach(self, session_id: str) -> dict[str, int | None]:
        with self._lock:
            session = self.get_or_throw(session_id)
            if not isinstance(session, TmuxSession):
                raise ValueError("detach is supported only for tmux lifecycle sessions")
            result = session.close("DETACH")
            self._sessions.pop(session_id, None)
            return result

    def close_all(self) -> None:
        with self._lock:
            for session in list(self._sessions.values()):
                try:
                    session.close("SIGTERM")
                except Exception:
                    pass
            self._sessions.clear()

    def _cleanup_dead_sessions(self) -> None:
        for sid, session in list(self._sessions.items()):
            if not session.is_alive:
                try:
                    session.close("SIGTERM")
                except Exception:
                    pass
                self._sessions.pop(sid, None)
