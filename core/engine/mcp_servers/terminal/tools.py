from __future__ import annotations

import asyncio
import os
import shlex
import subprocess

from mcp.server.fastmcp import FastMCP

from helpers import (
    _json,
    _profile_from_target,
    _sanitize_description,
    _sanitize_exec_command,
    _shell_wrap,
    resolve_key,
)
from operations import OperationManager
from sessions import SessionManager, TmuxSession
from ssh import SSHClientPool

# Module-level references set by register_tools()
_mcp: FastMCP | None = None
_session_manager: SessionManager | None = None
_ssh_pool: SSHClientPool | None = None
_operation_manager: OperationManager | None = None


def _run_local_exec(command: str, cwd: str | None, env: dict[str, str] | None, timeout_ms: int | None) -> tuple[str, str, int]:
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        command,
        shell=True,
        executable="/bin/bash",
        capture_output=True,
        text=True,
        cwd=cwd or os.getcwd(),
        env=full_env,
        timeout=(timeout_ms / 1000) if timeout_ms else None,
    )
    return proc.stdout, proc.stderr, proc.returncode


def register_tools(
    mcp: FastMCP,
    session_manager: SessionManager,
    ssh_pool: SSHClientPool,
    operation_manager: OperationManager,
) -> None:
    global _mcp, _session_manager, _ssh_pool, _operation_manager
    _mcp = mcp
    _session_manager = session_manager
    _ssh_pool = ssh_pool
    _operation_manager = operation_manager

    # ── exec_command ─────────────────────────────────────────────────────

    @mcp.tool()
    async def exec_command(
        command: str,
        target: str = "local",
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeoutMs: int | None = None,
        description: str = "",
    ) -> str:
        """Run a one-shot shell command on a local or SSH target and return stdout, stderr, and exit code."""
        if timeoutMs is not None and timeoutMs <= 0:
            raise ValueError("timeoutMs must be greater than 0")

        if target == "local":
            sanitized = _sanitize_exec_command(command, 2000)
            if description:
                sanitized = f"{sanitized} # {_sanitize_description(description)}"
            try:
                stdout, stderr, exit_code = _run_local_exec(sanitized, cwd, env, timeoutMs)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"local command timed out after {timeoutMs}ms") from exc
        else:
            profile = _profile_from_target(target)
            p = ssh_pool.get_profile(profile)
            sanitized = _sanitize_exec_command(command, p.max_chars)
            if description:
                sanitized = f"{sanitized} # {_sanitize_description(description)}"
            wrapped = _shell_wrap(sanitized, cwd, env)
            stdout, stderr, exit_code = ssh_pool.exec_command(profile, wrapped, timeoutMs)

        return _json(
            {
                "target": target,
                "success": exit_code == 0,
                "exitCode": exit_code,
                "stdout": stdout,
                "stderr": stderr,
            }
        )

    # ── sudo_exec_command ────────────────────────────────────────────────

    @mcp.tool()
    async def sudo_exec_command(
        command: str,
        target: str = "local",
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeoutMs: int | None = None,
        description: str = "",
    ) -> str:
        """Run a shell command with sudo privileges on a local or SSH target."""
        if timeoutMs is not None and timeoutMs <= 0:
            raise ValueError("timeoutMs must be greater than 0")

        if target == "local":
            sanitized = _sanitize_exec_command(command, 2000)
            if description:
                sanitized = f"{sanitized} # {_sanitize_description(description)}"
            wrapped = _shell_wrap(sanitized, cwd, env)
            sudo_cmd = f"sudo -n sh -c {shlex.quote(wrapped)}"
            try:
                stdout, stderr, exit_code = _run_local_exec(sudo_cmd, None, None, timeoutMs)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"local sudo command timed out after {timeoutMs}ms") from exc
        else:
            profile = _profile_from_target(target)
            p = ssh_pool.get_profile(profile)
            sanitized = _sanitize_exec_command(command, p.max_chars)
            if description:
                sanitized = f"{sanitized} # {_sanitize_description(description)}"
            wrapped = _shell_wrap(sanitized, cwd, env)
            stdout, stderr, exit_code = ssh_pool.sudo_exec_command(profile, wrapped, timeoutMs)

        return _json(
            {
                "target": target,
                "success": exit_code == 0,
                "exitCode": exit_code,
                "stdout": stdout,
                "stderr": stderr,
            }
        )

    # ── async operation runners ──────────────────────────────────────────

    async def _run_scp_upload_operation(
        operation_id: str,
        profile: str,
        target: str,
        local_path: str,
        remote_path: str,
    ) -> None:
        operation_manager.mark_running(operation_id)
        loop = asyncio.get_running_loop()

        def _progress(transferred: int, total: int) -> None:
            operation_manager.set_progress(operation_id, transferred, total)

        def _worker() -> str:
            return ssh_pool.scp_upload(profile, local_path, remote_path, progress_cb=_progress)

        try:
            message = await loop.run_in_executor(None, _worker)
            operation_manager.succeed(
                operation_id,
                {
                    "target": target,
                    "message": message,
                    "localPath": local_path,
                    "remotePath": remote_path,
                },
            )
        except Exception as exc:
            operation_manager.fail(operation_id, str(exc))

    async def _run_scp_download_operation(
        operation_id: str,
        profile: str,
        target: str,
        remote_path: str,
        local_path: str,
    ) -> None:
        operation_manager.mark_running(operation_id)
        loop = asyncio.get_running_loop()

        def _progress(transferred: int, total: int) -> None:
            operation_manager.set_progress(operation_id, transferred, total)

        def _worker() -> str:
            return ssh_pool.scp_download(profile, remote_path, local_path, progress_cb=_progress)

        try:
            message = await loop.run_in_executor(None, _worker)
            operation_manager.succeed(
                operation_id,
                {
                    "target": target,
                    "message": message,
                    "remotePath": remote_path,
                    "localPath": local_path,
                },
            )
        except Exception as exc:
            operation_manager.fail(operation_id, str(exc))

    async def _run_forward_remote_to_local_operation(
        operation_id: str,
        profile: str,
        target: str,
        remote_host: str,
        remote_port: int,
        local_port: int,
    ) -> None:
        operation_manager.mark_running(operation_id)
        loop = asyncio.get_running_loop()

        def _worker() -> tuple[str, int]:
            return ssh_pool.start_forward_remote_to_local(profile, remote_host, remote_port, local_port)

        try:
            tunnel_id, actual_port = await loop.run_in_executor(None, _worker)
            operation_manager.succeed(
                operation_id,
                {
                    "target": target,
                    "tunnelId": tunnel_id,
                    "localAddress": f"127.0.0.1:{actual_port}",
                    "remoteAddress": f"{remote_host}:{remote_port}",
                },
            )
        except Exception as exc:
            operation_manager.fail(operation_id, str(exc))

    async def _run_forward_local_to_remote_operation(
        operation_id: str,
        profile: str,
        target: str,
        local_host: str,
        local_port: int,
        remote_port: int,
        remote_host: str,
    ) -> None:
        operation_manager.mark_running(operation_id)
        loop = asyncio.get_running_loop()

        def _worker() -> tuple[str, int]:
            return ssh_pool.start_forward_local_to_remote(
                profile,
                local_host,
                local_port,
                remote_port,
                remote_host,
            )

        try:
            tunnel_id, actual_port = await loop.run_in_executor(None, _worker)
            operation_manager.succeed(
                operation_id,
                {
                    "target": target,
                    "tunnelId": tunnel_id,
                    "localAddress": f"{local_host}:{local_port}",
                    "remoteAddress": f"{remote_host}:{actual_port}",
                },
            )
        except Exception as exc:
            operation_manager.fail(operation_id, str(exc))

    # ── scp_upload ───────────────────────────────────────────────────────

    @mcp.tool()
    async def scp_upload(target: str, localPath: str, remotePath: str) -> str:
        """Start an asynchronous SFTP upload from localPath to remotePath on an SSH target."""
        profile = _profile_from_target(target)
        if not os.path.isfile(localPath):
            raise ValueError(f"Local file not found: {localPath}")

        op = operation_manager.create(
            operation_type="scp_upload",
            target=target,
            context={"localPath": localPath, "remotePath": remotePath},
        )
        asyncio.create_task(_run_scp_upload_operation(op.operation_id, profile, target, localPath, remotePath))
        return _json({"accepted": True, "operationId": op.operation_id, "status": op.status, "target": target})

    # ── scp_download ─────────────────────────────────────────────────────

    @mcp.tool()
    async def scp_download(target: str, remotePath: str, localPath: str) -> str:
        """Start an asynchronous SFTP download from an SSH target to localPath."""
        profile = _profile_from_target(target)
        local_dir = os.path.dirname(localPath)
        if local_dir and not os.path.isdir(local_dir):
            os.makedirs(local_dir, exist_ok=True)

        op = operation_manager.create(
            operation_type="scp_download",
            target=target,
            context={"remotePath": remotePath, "localPath": localPath},
        )
        asyncio.create_task(_run_scp_download_operation(op.operation_id, profile, target, remotePath, localPath))
        return _json({"accepted": True, "operationId": op.operation_id, "status": op.status, "target": target})

    # ── forward_remote_to_local ──────────────────────────────────────────

    @mcp.tool()
    async def forward_remote_to_local(
        target: str,
        remoteHost: str,
        remotePort: int,
        localPort: int = 0,
    ) -> str:
        """Start an SSH local port-forward from localPort to remoteHost:remotePort."""
        profile = _profile_from_target(target)
        if remotePort <= 0 or remotePort > 65535:
            raise ValueError("remotePort must be in range 1..65535")
        if localPort < 0 or localPort > 65535:
            raise ValueError("localPort must be in range 0..65535")

        op = operation_manager.create(
            operation_type="forward_remote_to_local",
            target=target,
            context={"remoteHost": remoteHost, "remotePort": str(remotePort), "localPort": str(localPort)},
        )
        asyncio.create_task(
            _run_forward_remote_to_local_operation(
                op.operation_id,
                profile,
                target,
                remoteHost,
                remotePort,
                localPort,
            )
        )
        return _json({"accepted": True, "operationId": op.operation_id, "status": op.status, "target": target})

    # ── forward_local_to_remote ──────────────────────────────────────────

    @mcp.tool()
    async def forward_local_to_remote(
        target: str,
        localHost: str,
        localPort: int,
        remotePort: int,
        remoteHost: str = "127.0.0.1",
    ) -> str:
        """Start an SSH remote port-forward from remotePort to localHost:localPort."""
        profile = _profile_from_target(target)
        if localPort <= 0 or localPort > 65535:
            raise ValueError("localPort must be in range 1..65535")
        if remotePort < 0 or remotePort > 65535:
            raise ValueError("remotePort must be in range 0..65535")

        op = operation_manager.create(
            operation_type="forward_local_to_remote",
            target=target,
            context={
                "localHost": localHost,
                "localPort": str(localPort),
                "remoteHost": remoteHost,
                "remotePort": str(remotePort),
            },
        )
        asyncio.create_task(
            _run_forward_local_to_remote_operation(
                op.operation_id,
                profile,
                target,
                localHost,
                localPort,
                remotePort,
                remoteHost,
            )
        )
        return _json({"accepted": True, "operationId": op.operation_id, "status": op.status, "target": target})

    # ── tunnel_stop ──────────────────────────────────────────────────────

    @mcp.tool()
    async def tunnel_stop(tunnelId: str) -> str:
        """Stop an active SSH tunnel by tunnel ID."""
        message = ssh_pool.stop_tunnel(tunnelId)
        return _json({"success": True, "message": message})

    # ── tunnel_list ──────────────────────────────────────────────────────

    @mcp.tool()
    async def tunnel_list() -> str:
        """List all active SSH tunnels managed by this server."""
        return _json({"tunnels": ssh_pool.list_tunnels()})

    # ── get_operation_status ─────────────────────────────────────────────

    @mcp.tool()
    async def get_operation_status(operationId: str) -> str:
        """Get status for an async SCP or tunnel operation by operation ID."""
        payload = operation_manager.as_dict(operationId)
        result = payload.get("result")
        if isinstance(result, dict):
            tunnel_id = result.get("tunnelId")
            if isinstance(tunnel_id, str) and tunnel_id:
                try:
                    payload["tunnel"] = ssh_pool.get_tunnel(tunnel_id)
                except Exception as exc:
                    payload["tunnelError"] = str(exc)
        return _json(payload)

    # ── open_session ─────────────────────────────────────────────────────

    @mcp.tool()
    async def open_session(
        command: str,
        args: list[str] | None = None,
        target: str = "local",
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        transport: str = "auto",
        lifecycle: str = "direct",
        cols: int = 80,
        rows: int = 24,
    ) -> str:
        """Start an interactive terminal session and return a session ID."""
        if not command or not command.strip():
            raise ValueError("command is required")
        if not 10 <= cols <= 500:
            raise ValueError("cols must be between 10 and 500")
        if not 5 <= rows <= 200:
            raise ValueError("rows must be between 5 and 200")

        session = session_manager.create(
            target=target,
            command=command,
            args=args,
            cwd=cwd,
            env=env,
            transport=transport,
            lifecycle=lifecycle,
            cols=cols,
            rows=rows,
        )
        await asyncio.sleep(0.2)
        snapshot = session.get_snapshot()
        return _json(
            {
                "sessionId": session.id,
                "target": session.target,
                "pid": session.pid,
                "cols": session.size["cols"],
                "rows": session.size["rows"],
                "transport": session.transport,
                "lifecycle": session.lifecycle,
                "initialScreen": snapshot["text"],
            }
        )

    # ── send_session_input ───────────────────────────────────────────────

    @mcp.tool()
    async def send_session_input(
        sessionId: str,
        input: str | None = None,
        specialKey: str | None = None,
        waitMs: int = 100,
    ) -> str:
        """Send text or a special key to a session and return the updated screen snapshot."""
        if waitMs < 0 or waitMs > 10000:
            raise ValueError("waitMs must be between 0 and 10000")

        session = session_manager.get_or_throw(sessionId)
        if specialKey:
            if isinstance(session, TmuxSession):
                session.send_special(specialKey)
            else:
                session.write(resolve_key(specialKey))
        elif input is not None:
            session.write(input)
        else:
            raise ValueError("Either input or specialKey must be provided")

        await asyncio.sleep(waitMs / 1000)
        snapshot = session.get_snapshot()
        return _json(
            {
                "success": True,
                "target": session.target,
                "transport": session.transport,
                "lifecycle": session.lifecycle,
                "screen": snapshot["text"],
                "cursorPosition": snapshot["cursorPosition"],
            }
        )

    # ── capture_session_screen ───────────────────────────────────────────

    @mcp.tool()
    async def capture_session_screen(
        sessionId: str,
        includeScrollback: bool = False,
        format: str = "text",
    ) -> str:
        """Capture a terminal session screen as text, ansi, or structured output."""
        session = session_manager.get_or_throw(sessionId)
        fmt = format.lower()
        if fmt == "detailed":
            fmt = "structured"
        if fmt not in {"text", "ansi", "structured"}:
            raise ValueError("format must be one of: text, ansi, structured (or detailed)")

        if fmt == "ansi":
            return _json({"ansiData": session.get_ansi_snapshot()})

        snapshot = session.get_snapshot(includeScrollback)
        if fmt == "structured":
            out = dict(snapshot)
            out["target"] = session.target
            out["transport"] = session.transport
            out["lifecycle"] = session.lifecycle
            return _json(out)

        return _json(
            {
                "screen": snapshot["text"],
                "cursorPosition": snapshot["cursorPosition"],
                "terminalSize": snapshot["terminalSize"],
                "target": session.target,
                "transport": session.transport,
                "lifecycle": session.lifecycle,
            }
        )

    # ── resize_tmux_session ──────────────────────────────────────────────

    @mcp.tool()
    async def resize_tmux_session(sessionId: str, cols: int, rows: int) -> str:
        """Resize a tmux-backed session and return the updated screen snapshot."""
        if not 10 <= cols <= 500:
            raise ValueError("cols must be between 10 and 500")
        if not 5 <= rows <= 200:
            raise ValueError("rows must be between 5 and 200")

        session = session_manager.get_or_throw(sessionId)
        if not isinstance(session, TmuxSession):
            raise ValueError("resize_tmux_session supports only tmux lifecycle sessions")
        previous_size = session.resize(cols, rows)
        await asyncio.sleep(0.1)
        snapshot = session.get_snapshot()
        return _json(
            {
                "success": True,
                "target": session.target,
                "transport": session.transport,
                "lifecycle": session.lifecycle,
                "previousSize": previous_size,
                "newSize": session.size,
                "screen": snapshot["text"],
            }
        )

    # ── list_sessions ────────────────────────────────────────────────────

    @mcp.tool()
    async def list_sessions() -> str:
        """List terminal sessions currently tracked by this MCP server."""
        return _json({"sessions": session_manager.list()})

    # ── list_tmux_sessions ───────────────────────────────────────────────

    @mcp.tool()
    async def list_tmux_sessions(target: str = "local") -> str:
        """List tmux sessions on a local or SSH target."""
        sessions = session_manager.list_tmux(target)
        return _json({"target": target, "tmuxSessions": sessions})

    # ── attach_tmux_session ──────────────────────────────────────────────

    @mcp.tool()
    async def attach_tmux_session(
        sessionRef: str | None = None,
        paneRef: str | None = None,
        target: str = "local",
        cols: int = 80,
        rows: int = 24,
    ) -> str:
        """Attach MCP control to an existing tmux session or pane."""
        session_ref = (sessionRef or "").strip()
        pane_ref = (paneRef or "").strip()
        if not session_ref and not pane_ref:
            raise ValueError("Either sessionRef or paneRef is required")
        if not 10 <= cols <= 500:
            raise ValueError("cols must be between 10 and 500")
        if not 5 <= rows <= 200:
            raise ValueError("rows must be between 5 and 200")

        session = session_manager.attach_tmux(
            target=target,
            tmux_session_name=session_ref or None,
            tmux_pane_ref=pane_ref or None,
            cols=cols,
            rows=rows,
        )
        await asyncio.sleep(0.1)
        snapshot = session.get_snapshot()
        return _json(
            {
                "sessionId": session.id,
                "target": session.target,
                "pid": session.pid,
                "cols": session.size["cols"],
                "rows": session.size["rows"],
                "transport": session.transport,
                "lifecycle": session.lifecycle,
                "sessionRef": session_ref or None,
                "paneRef": pane_ref or None,
                "initialScreen": snapshot["text"],
            }
        )

    # ── detach_tmux_session ──────────────────────────────────────────────

    @mcp.tool()
    async def detach_tmux_session(sessionId: str) -> str:
        """Detach MCP from a tmux-backed session while keeping the tmux workload running."""
        result = session_manager.detach(sessionId)
        return _json(
            {
                "success": True,
                "action": "detach",
                "exitCode": result["exitCode"],
                "signal": result["signal"],
            }
        )

    # ── terminate_session ────────────────────────────────────────────────

    @mcp.tool()
    async def terminate_session(sessionId: str, signal: str = "SIGTERM") -> str:
        """Terminate a terminal session by ID and remove it from MCP tracking."""
        allowed = {"SIGTERM", "SIGKILL", "SIGHUP"}
        signal_name = signal.upper()
        if signal_name not in allowed:
            raise ValueError("signal must be one of SIGTERM, SIGKILL, SIGHUP")

        result = session_manager.terminate(sessionId, signal_name)
        return _json(
            {
                "success": True,
                "action": "terminate",
                "exitCode": result["exitCode"],
                "signal": result["signal"],
            }
        )
