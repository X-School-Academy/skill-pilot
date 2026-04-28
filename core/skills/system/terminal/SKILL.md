---
name: terminal
description: "Run shell commands, manage interactive terminal sessions, SSH tunnels, file transfers, and tmux sessions on local or remote hosts."
---

## Tools

Select the tool that matches the task. Read its reference file only when you are ready to invoke it.

- **attach_tmux_session** — Attach MCP control to an existing tmux session or pane. ([details](references/attach_tmux_session.md))
- **capture_session_screen** — Capture a terminal session screen as text, ansi, or structured output. ([details](references/capture_session_screen.md))
- **detach_tmux_session** — Detach MCP from a tmux-backed session while keeping the tmux workload running. ([details](references/detach_tmux_session.md))
- **exec_command** — Run a one-shot shell command on a local or SSH target and return stdout, stderr, and exit code. ([details](references/exec_command.md))
- **forward_local_to_remote** — Start an SSH remote port-forward from remotePort to localHost:localPort. ([details](references/forward_local_to_remote.md))
- **forward_remote_to_local** — Start an SSH local port-forward from localPort to remoteHost:remotePort. ([details](references/forward_remote_to_local.md))
- **get_operation_status** — Get status for an async SCP or tunnel operation by operation ID. ([details](references/get_operation_status.md))
- **list_sessions** — List terminal sessions currently tracked by this MCP server. ([details](references/list_sessions.md))
- **list_tmux_sessions** — List tmux sessions on a local or SSH target. ([details](references/list_tmux_sessions.md))
- **open_session** — Start an interactive local or remote SSH terminal session and return a session ID. ([details](references/open_session.md))
- **resize_tmux_session** — Resize a tmux-backed session and return the updated screen snapshot. ([details](references/resize_tmux_session.md))
- **scp_download** — Start an asynchronous SFTP download from an SSH target to localPath. ([details](references/scp_download.md))
- **scp_upload** — Start an asynchronous SFTP upload from localPath to remotePath on an SSH target. ([details](references/scp_upload.md))
- **send_session_input** — Send text or a special key to a session and return the updated screen snapshot. ([details](references/send_session_input.md))
- **sudo_exec_command** — Run a shell command with sudo privileges on a local or SSH target. ([details](references/sudo_exec_command.md))
- **terminate_session** — Terminate a terminal session by ID and remove it from MCP tracking. ([details](references/terminate_session.md))
- **tunnel_list** — List all active SSH tunnels managed by this server. ([details](references/tunnel_list.md))
- **tunnel_stop** — Stop an active SSH tunnel by tunnel ID. ([details](references/tunnel_stop.md))
