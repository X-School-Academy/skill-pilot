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
        """Run a one-shot shell command on a local or SSH target and return stdout, stderr, and exit code.

        Use this tool when you need to execute a shell command and capture its output.
        Best for short-lived commands that complete within the timeout window.

        Args:
            command: The shell command to run. Maximum 2000 characters for local; SSH profile maxChars applies for remote.
                     Examples: "ls -la /app", "docker ps", "cat /etc/os-release"
            target: Where to run the command.
                     - "local" — run on the local machine (default)
                     - "ssh:<profile>" — run on a remote SSH host defined in config.json, e.g. "ssh:prod", "ssh:dev"
            cwd: Working directory for the command. Defaults to the current working directory.
                 Example: "/app" or "/home/deploy"
            env: Additional environment variables to merge into the process environment.
                 Example: {"DEBUG": "1", "PORT": "8080"}
            timeoutMs: Timeout in milliseconds. Must be greater than 0 if provided.
                       Example: 30000 for a 30-second timeout.
            description: Human-readable label appended as a comment in the command string for audit trails.
                         Example: "check disk usage"

        Returns:
            JSON object with:
            - target: the target used
            - success: true if exit code is 0
            - exitCode: integer exit code
            - stdout: captured standard output
            - stderr: captured standard error

        Do not use this tool:
            - to start long-running or interactive processes; use open_session instead
            - when sudo access is required; use sudo_exec_command instead

        Notes:
            - Local commands run via /bin/bash with shell=True.
            - SSH commands are wrapped with cwd and env handling before execution.
        """
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
        """Run a shell command with sudo privileges on a local or SSH target.

        Use this tool when you need to execute a command requiring elevated privileges.
        Best for system administration tasks such as package installation or service management.

        Args:
            command: The shell command to run with sudo. Maximum 2000 characters for local; SSH profile maxChars applies for remote.
                     Examples: "systemctl restart nginx", "apt install -y curl", "chmod 600 /etc/secret"
            target: Where to run the command.
                     - "local" — run on the local machine (default)
                     - "ssh:<profile>" — run on a remote SSH host, e.g. "ssh:prod", "ssh:dev"
            cwd: Working directory for the command. Defaults to the current working directory.
            env: Additional environment variables to merge into the process environment.
                 Example: {"DEBIAN_FRONTEND": "noninteractive"}
            timeoutMs: Timeout in milliseconds. Must be greater than 0 if provided.
                       Example: 60000 for a 60-second timeout.
            description: Human-readable label appended as a comment in the command string for audit trails.

        Returns:
            JSON object with:
            - target: the target used
            - success: true if exit code is 0
            - exitCode: integer exit code
            - stdout: captured standard output
            - stderr: captured standard error

        Do not use this tool:
            - when sudo access is not required; use exec_command instead
            - to start interactive sessions; use open_session instead

        Notes:
            - Requires passwordless sudo configured on the target machine (sudo -n).
            - For SSH targets, set sudoPassword in the SSH profile if the host requires a password.
            - Local commands are wrapped with sudo -n sh -c before execution.
        """
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
        """Start an asynchronous SFTP upload from localPath to remotePath on an SSH target.

        Use this tool when you need to transfer a local file to a remote SSH host.
        Best for uploading configuration files, binaries, or other artifacts to remote servers.

        Args:
            target: SSH profile identifying the remote host. Must be "ssh:<profile>" (e.g. "ssh:prod", "ssh:dev").
                    Profiles are defined in the server's SSH config file (config.json).
            localPath: Absolute path to the local file to upload. The file must exist before calling.
                       Example: "/home/user/deploy.tar.gz"
            remotePath: Destination path on the remote host.
                        Example: "/opt/app/deploy.tar.gz"

        Returns:
            JSON object with:
            - accepted: true when the operation has been queued
            - operationId: ID to track progress via get_operation_status
            - status: initial operation status (e.g. "pending")
            - target: the SSH target used

        Do not use this tool:
            - to download files from a remote host; use scp_download instead
            - for local-to-local file operations; use exec_command with cp instead
            - with target="local"; this tool only supports SSH targets

        Notes:
            - The upload runs asynchronously. Poll get_operation_status with the operationId for completion.
            - The local file must exist before calling this tool.
        """
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
        """Start an asynchronous SFTP download from an SSH target to localPath.

        Use this tool when you need to retrieve a file from a remote SSH host to the local machine.
        Best for fetching logs, outputs, or artifacts generated on a remote server.

        Args:
            target: SSH profile identifying the remote host. Must be "ssh:<profile>" (e.g. "ssh:prod", "ssh:dev").
                    Profiles are defined in the server's SSH config file (config.json).
            remotePath: Path to the file on the remote host.
                        Example: "/var/log/app.log", "/opt/app/output.tar.gz"
            localPath: Destination path on the local machine. Parent directories are created if needed.
                       Example: "/tmp/app.log", "/home/user/downloads/output.tar.gz"

        Returns:
            JSON object with:
            - accepted: true when the operation has been queued
            - operationId: ID to track progress via get_operation_status
            - status: initial operation status (e.g. "pending")
            - target: the SSH target used

        Do not use this tool:
            - to upload files to a remote host; use scp_upload instead
            - with target="local"; this tool only supports SSH targets

        Notes:
            - The download runs asynchronously. Poll get_operation_status with the operationId for completion.
            - Local parent directories are created automatically if they do not exist.
        """
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
        """Start an SSH local port-forward from localPort to remoteHost:remotePort.

        Use this tool when you need to access a service on a remote network through an SSH tunnel.
        Best for reaching databases, internal APIs, or other services behind an SSH gateway.
        Equivalent to: ssh -L localPort:remoteHost:remotePort <target>

        Args:
            target: SSH profile identifying the tunnel endpoint. Must be "ssh:<profile>" (e.g. "ssh:prod", "ssh:dev").
                    Profiles are defined in the server's SSH config file (config.json).
            remoteHost: Hostname or IP of the service to reach on the remote network.
                        Use "localhost" to reach a service running on the SSH host itself.
                        Example: "localhost", "db.internal", "10.0.1.5"
            remotePort: Port of the remote service. Must be in range 1..65535.
                        Example: 5432 for PostgreSQL, 3306 for MySQL, 6379 for Redis.
            localPort: Local port to bind. Use 0 to let the OS assign an available port.
                       Example: 5432 to bind locally on the same port, 0 for auto-assign.

        Returns:
            JSON object with:
            - accepted: true when the tunnel operation has been queued
            - operationId: ID to track tunnel status via get_operation_status
            - status: initial operation status
            - target: the SSH target used

        Do not use this tool:
            - to expose a local service on a remote host; use forward_local_to_remote instead
            - to stop a tunnel; use tunnel_stop instead
            - with target="local"; this tool only supports SSH targets

        Notes:
            - The tunnel is established asynchronously. Poll get_operation_status for tunnelId and localAddress.
            - If localPort is 0, the actual assigned port is returned in the operation result as localAddress.
        """
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
        """Start an SSH remote port-forward from remotePort to localHost:localPort.

        Use this tool when you need to expose a local service on a remote SSH host's port.
        Best for making a locally running service accessible from a remote machine.
        Equivalent to: ssh -R remotePort:localHost:localPort <target>

        Args:
            target: SSH profile identifying the tunnel endpoint. Must be "ssh:<profile>" (e.g. "ssh:prod", "ssh:dev").
                    Profiles are defined in the server's SSH config file (config.json).
            localHost: Hostname or IP of the local service to expose.
                       Use "localhost" to expose a service running on the local machine.
                       Example: "localhost", "127.0.0.1"
            localPort: Port of the local service. Must be in range 1..65535.
                       Example: 8080 for a local web server, 3000 for a dev server.
            remotePort: Port to bind on the remote host. Use 0 to let the OS assign a port.
                        Example: 9000 to expose as port 9000 on the remote machine.
            remoteHost: Interface to bind on the remote host. Defaults to "127.0.0.1" (loopback only).
                        Use "0.0.0.0" to expose on all remote interfaces (requires GatewayPorts on SSH server).

        Returns:
            JSON object with:
            - accepted: true when the tunnel operation has been queued
            - operationId: ID to track tunnel status via get_operation_status
            - status: initial operation status
            - target: the SSH target used

        Do not use this tool:
            - to access a remote service locally; use forward_remote_to_local instead
            - to stop a tunnel; use tunnel_stop instead
            - with target="local"; this tool only supports SSH targets

        Notes:
            - The tunnel is established asynchronously. Poll get_operation_status for tunnelId and remoteAddress.
            - If remotePort is 0, the actual assigned port is returned in the operation result as remoteAddress.
        """
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
        """Stop an active SSH tunnel by tunnel ID.

        Use this tool when you need to close a previously established port-forward tunnel.
        Best for cleanup after a task is done or when the forwarded service is no longer needed.

        Args:
            tunnelId: The tunnel ID returned in the result of forward_remote_to_local or forward_local_to_remote.
                      Retrieve it by calling get_operation_status(operationId) and reading result.tunnelId.
                      Example: "tunnel-abc123"

        Returns:
            JSON object with:
            - success: true if the tunnel was stopped
            - message: confirmation message from the SSH pool

        Do not use this tool:
            - to list active tunnels; use tunnel_list instead
        """
        message = ssh_pool.stop_tunnel(tunnelId)
        return _json({"success": True, "message": message})

    # ── tunnel_list ──────────────────────────────────────────────────────

    @mcp.tool()
    async def tunnel_list() -> str:
        """List all active SSH tunnels managed by this server.

        Use this tool when you need to see which port-forward tunnels are currently open.
        Best for auditing active connections or finding a tunnelId before calling tunnel_stop.

        Returns:
            JSON object with:
            - tunnels: list of active tunnel objects, each containing tunnelId, direction, localAddress, and remoteAddress.

        Do not use this tool:
            - to stop a tunnel; use tunnel_stop instead
        """
        return _json({"tunnels": ssh_pool.list_tunnels()})

    # ── get_operation_status ─────────────────────────────────────────────

    @mcp.tool()
    async def get_operation_status(operationId: str) -> str:
        """Get status for an async SCP or tunnel operation by operation ID.

        Use this tool when you need to check if an asynchronous file transfer or tunnel setup has completed.
        Best for polling after scp_upload, scp_download, forward_remote_to_local, or forward_local_to_remote.

        Args:
            operationId: The operation ID returned in the accepted response of the async operation.
                         Example: "op-abc123" (from scp_upload, scp_download, forward_remote_to_local, or forward_local_to_remote)

        Returns:
            JSON object with:
            - operationId: the operation ID
            - status: current status — "pending", "running", "succeeded", or "failed"
            - result: result data when succeeded. For SCP: {localPath, remotePath, message}. For tunnels: {tunnelId, localAddress, remoteAddress}.
            - error: error message string when status is "failed"
            - tunnel: live tunnel info object if the operation created a tunnel (includes tunnelId)

        Notes:
            - Poll periodically (e.g. every 1–2 seconds) until status is "succeeded" or "failed".
            - For tunnel operations, read result.tunnelId then pass it to tunnel_stop when done.
            - For SCP operations, result.message contains a human-readable completion summary.
        """
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
        """Start an interactive local or remote SSH terminal session and return a session ID.

        Use this tool when you need to run a long-running or interactive process such as a shell, REPL, or server.
        Best for processes that produce output over time or require ongoing input.

        Args:
            command: The executable to run. Required.
                     Examples: "bash", "python3", "node", "ssh prod -t bash"
                     For SSH via local tmux (Method 2 / fast): use "ssh prod -t 'bash'" with target="local".
            args: Optional list of arguments to pass to the command.
                  Example: ["-i", "--verbose"]
            target: Where to run the session.
                     - "local" — run on the local machine (default). Also use this for local tmux wrapping an SSH command.
                     - "ssh:<profile>" — run directly on a remote SSH host, e.g. "ssh:prod", "ssh:dev".
                       Profiles are defined in the server's SSH config file (config.json).
            cwd: Working directory for the session. Example: "/app"
            env: Additional environment variables. Example: {"RAILS_ENV": "production"}
            transport: I/O transport mode.
                     - "auto" — automatically picks pty for interactive CLIs, pipe otherwise (default, recommended)
                     - "pty" — force pseudo-terminal; use for interactive programs (vim, python REPL, bash prompts)
                     - "pipe" — force stdin/stdout/stderr pipes; use for non-interactive scripts
            lifecycle: Session lifecycle mode.
                     - "direct" — run process directly in the foreground (default)
                     - "tmux" — wrap in a tmux session; survives agent disconnection; required for long-running background tasks
            cols: Terminal width in columns. Must be between 10 and 500. Default: 80.
            rows: Terminal height in rows. Must be between 5 and 200. Default: 24.

        Returns:
            JSON object with:
            - sessionId: unique ID used for all subsequent session operations (send_session_input, capture_session_screen, etc.)
            - target: the target used
            - pid: process ID of the started process
            - cols: actual terminal width
            - rows: actual terminal height
            - transport: transport mode in use
            - lifecycle: lifecycle mode in use
            - initialScreen: text snapshot of the terminal screen after startup

        Do not use this tool:
            - for simple one-shot commands; use exec_command instead
            - when sudo is needed for a one-shot command; use sudo_exec_command instead

        Notes:
            - Use send_session_input to send input and capture_session_screen to read output.
            - Use lifecycle="tmux" for background tasks that must survive agent disconnection.
            - For high-frequency interactions with remote hosts, prefer target="local" with command="ssh <profile> -t bash" and lifecycle="tmux" (Method 2 — 10x faster than target="ssh:<profile>").
            - Always terminate or detach sessions when done to avoid resource leaks.
        """
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
        """Send text or a special key to a session and return the updated screen snapshot.

        Use this tool when you need to interact with a running terminal session by typing text or pressing keys.
        Best for driving interactive programs such as shells, REPLs, menus, or prompts.

        Args:
            sessionId: ID of the session returned by open_session or attach_tmux_session.
                       Example: "sess-abc123"
            input: Text string to write to the terminal. Provide either input or specialKey, not both.
                   To run a shell command, append a newline: "ls -la\n", "cd /app\n", "exit\n"
                   To type text without submitting: "hello world" (no newline)
            specialKey: Named key to send instead of text. Provide either specialKey or input, not both.
                        Supported values: "Enter", "Tab", "Escape", "Backspace", "Delete",
                        "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
                        "Ctrl-C" (interrupt), "Ctrl-D" (EOF/logout), "Ctrl-Z" (suspend),
                        "shift+ArrowUp", "alt+ArrowLeft", "ctrl+ArrowRight"
            waitMs: Milliseconds to wait after sending input before capturing the screen.
                    Must be between 0 and 10000. Default: 100.
                    Increase for slow commands: 500–2000ms. Use 0 for instant capture.

        Returns:
            JSON object with:
            - success: true if input was delivered
            - target: the session target
            - transport: transport mode in use
            - lifecycle: lifecycle mode in use
            - screen: text snapshot of the terminal after waiting
            - cursorPosition: current cursor position as {row, col}

        Do not use this tool:
            - to read the screen without sending input; use capture_session_screen instead
            - for one-shot commands that do not need interaction; use exec_command instead
        """
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
        """Capture a terminal session screen as text, ansi, or structured output.

        Use this tool when you need to read the current output of a running terminal session.
        Best for polling a session for results, checking prompts, or extracting structured data.

        Args:
            sessionId: ID of the session returned by open_session or attach_tmux_session.
                       Example: "sess-abc123"
            includeScrollback: If true, include scrollback buffer content above the visible screen area.
                               Default: false. Set to true to read command history or output that has scrolled off.
            format: Output format. Default: "text".
                     - "text" — plain text content of the visible screen (recommended for most use cases)
                     - "ansi" — raw ANSI escape sequences; use when color/style information is needed
                     - "structured" — full metadata object with cursor position, terminal size, and session info; also accepts "detailed" as an alias

        Returns:
            For "text" format, JSON object with:
            - screen: visible terminal text
            - cursorPosition: current cursor position as {row, col}
            - terminalSize: {cols, rows}
            - target, transport, lifecycle: session metadata
            For "ansi" format, JSON object with:
            - ansiData: raw ANSI-encoded terminal content
            For "structured" format, full snapshot dict with target, transport, and lifecycle fields added.

        Do not use this tool:
            - to send input to the session; use send_session_input instead
        """
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
        """Resize a tmux-backed session and return the updated screen snapshot.

        Use this tool when you need to change the terminal dimensions of a tmux session.
        Best for adjusting the viewport before capturing output or when the display appears malformed.

        Args:
            sessionId: ID of the tmux session returned by open_session (with lifecycle="tmux") or attach_tmux_session.
                       Example: "sess-abc123"
            cols: New terminal width in columns. Must be between 10 and 500.
                  Example: 220 for a wide terminal, 80 for standard width.
            rows: New terminal height in rows. Must be between 5 and 200.
                  Example: 50 for tall output, 24 for standard height.

        Returns:
            JSON object with:
            - success: true if resize succeeded
            - target, transport, lifecycle: session metadata
            - previousSize: {cols, rows} before the resize
            - newSize: {cols, rows} after the resize
            - screen: text snapshot of the terminal after the resize

        Do not use this tool:
            - on non-tmux sessions; this tool only supports lifecycle="tmux" sessions
        """
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
        """List terminal sessions currently tracked by this MCP server.

        Use this tool when you need to see which sessions are active and retrieve their session IDs.
        Best for finding an existing session before sending input or capturing its screen.

        Returns:
            JSON object with:
            - sessions: list of session summary objects, each containing sessionId, target, transport, lifecycle, pid, and size.

        Do not use this tool:
            - to list tmux sessions running on the system; use list_tmux_sessions instead
        """
        return _json({"sessions": session_manager.list()})

    # ── list_tmux_sessions ───────────────────────────────────────────────

    @mcp.tool()
    async def list_tmux_sessions(target: str = "local") -> str:
        """List tmux sessions on a local or SSH target.

        Use this tool when you need to enumerate existing tmux sessions running on the system.
        Best for discovering named tmux sessions before attaching to them with attach_tmux_session.

        Args:
            target: Where to query for tmux sessions.
                     - "local" — list tmux sessions on the local machine (default)
                     - "ssh:<profile>" — list tmux sessions on a remote SSH host, e.g. "ssh:prod", "ssh:dev"
                       Profiles are defined in the server's SSH config file (config.json).

        Returns:
            JSON object with:
            - target: the target queried
            - tmuxSessions: list of tmux session descriptors (name, windows, created, attached status, etc.)

        Do not use this tool:
            - to list MCP-tracked sessions; use list_sessions instead
            - to attach to a tmux session; use attach_tmux_session instead
        """
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
        """Attach MCP control to an existing tmux session or pane.

        Use this tool when you need to interact with a tmux session already running on the system.
        Best for reconnecting to background processes or long-running tasks started outside this MCP server.

        Args:
            sessionRef: Name of the tmux session to attach. Provide either sessionRef or paneRef, not both.
                        Use the session name as shown by list_tmux_sessions or `tmux ls`.
                        Example: "work", "training", "mcp-abc123"
                        When using sessionRef, MCP attaches to pane 0 of window 0 by default (session:0.0).
            paneRef: Tmux pane reference to attach to a specific pane. Provide either paneRef or sessionRef.
                     Format: "<session>:<window>.<pane>" — e.g. "work:0.1", "training:1.0"
                     Use this when you need to target a pane other than the default (0.0).
            target: Where the tmux session is running.
                     - "local" — the local machine (default)
                     - "ssh:<profile>" — a remote SSH host, e.g. "ssh:prod", "ssh:dev"
                       Profiles are defined in the server's SSH config file (config.json).
            cols: Terminal width in columns. Must be between 10 and 500. Default: 80.
            rows: Terminal height in rows. Must be between 5 and 200. Default: 24.

        Returns:
            JSON object with:
            - sessionId: MCP session ID for subsequent operations (send_session_input, capture_session_screen, etc.)
            - target, transport, lifecycle: session metadata
            - pid: process ID
            - cols, rows: terminal dimensions in use
            - sessionRef: the session name used (if provided)
            - paneRef: the pane reference used (if provided)
            - initialScreen: text snapshot of the terminal after attaching

        Do not use this tool:
            - to create a new session from scratch; use open_session instead
            - to discover available tmux sessions first; use list_tmux_sessions
        """
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
        """Detach MCP from a tmux-backed session while keeping the tmux workload running.

        Use this tool when you want to stop monitoring a tmux session without killing the underlying process.
        Best for background tasks that should continue running after the agent disconnects.

        Args:
            sessionId: ID of the MCP-tracked tmux session to detach. Must have been opened with lifecycle="tmux".
                       Use list_sessions to find active session IDs.
                       Example: "sess-abc123"

        Returns:
            JSON object with:
            - success: true if detach succeeded
            - action: "detach"
            - exitCode: exit code of the MCP wrapper process
            - signal: signal used to stop the wrapper (if any)

        Do not use this tool:
            - to stop the underlying process entirely; use terminate_session instead
            - on non-tmux sessions; only lifecycle="tmux" sessions can be detached
            - to re-attach later; use attach_tmux_session with the original tmux session name
        """
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
        """Terminate a terminal session by ID and remove it from MCP tracking.

        Use this tool when you are done with a terminal session and want to stop its process.
        Best for cleanup after a task completes or when a session becomes unresponsive.

        Args:
            sessionId: ID of the session to terminate. Use list_sessions to find active session IDs.
                       Example: "sess-abc123"
            signal: Signal to send to the process. Default: "SIGTERM".
                     - "SIGTERM" — graceful shutdown; gives the process time to clean up (recommended)
                     - "SIGKILL" — force kill immediately; use when SIGTERM does not stop the process
                     - "SIGHUP" — hangup; simulates a terminal disconnect (useful for daemons that reload on SIGHUP)

        Returns:
            JSON object with:
            - success: true if termination succeeded
            - action: "terminate"
            - exitCode: exit code after termination
            - signal: signal used to terminate

        Do not use this tool:
            - when you want to keep the tmux process running in the background; use detach_tmux_session instead
            - to list sessions; use list_sessions instead
        """
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
