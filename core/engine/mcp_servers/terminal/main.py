#!/usr/bin/env python3
"""
Terminal MCP Server

Unified terminal session server for local and SSH targets.

Run:
    uv run mcp-servers/terminal/main.py

Optional SSH profiles:
    uv run mcp-servers/terminal/main.py --sshConfig=mcp-servers/terminal/config.json

Tools:
    open_session
    attach_tmux_session
    send_session_input
    capture_session_screen
    resize_tmux_session
    list_sessions
    list_tmux_sessions
    detach_tmux_session
    terminate_session
    exec_command
    sudo_exec_command
    scp_upload
    scp_download
    forward_remote_to_local
    forward_local_to_remote
    tunnel_stop
    tunnel_list
    get_operation_status
"""

from __future__ import annotations

import argparse
import os
import signal

from mcp.server.fastmcp import FastMCP

from operations import OperationManager
from sessions import SessionManager
from ssh import SSHClientPool
from tools import register_tools


class _Config:
    ssh_config: str | None = None


cfg = _Config()
ssh_pool = SSHClientPool()
session_manager = SessionManager(ssh_pool)
operation_manager = OperationManager()
mcp = FastMCP("Terminal MCP Server")

register_tools(mcp, session_manager, ssh_pool, operation_manager)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Terminal MCP Server")
    p.add_argument(
        "--sshConfig",
        default=None,
        help="Path to SSH profile config JSON5 (profiles map).",
    )
    return p.parse_args()


def _cleanup_and_exit(*_args) -> None:
    session_manager.close_all()
    ssh_pool.close_all()
    raise SystemExit(0)


def main() -> None:
    if os.name != "posix":
        raise RuntimeError("Terminal MCP server supports only POSIX hosts (Linux/macOS)")

    args = parse_args()
    cfg.ssh_config = args.sshConfig
    ssh_pool.load_profiles(cfg.ssh_config)

    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)

    try:
        mcp.run(transport="stdio")
    finally:
        session_manager.close_all()
        ssh_pool.close_all()


if __name__ == "__main__":
    main()
