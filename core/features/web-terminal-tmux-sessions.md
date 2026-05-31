# Feature Retrieval Index: Web Terminal and Tmux Sessions

## Retrieval Keywords

terminal, tmux, session, WebSocket, xterm, ttyd, web terminal, browser terminal, attach, kill, cleanup, history, saved history, terminal history, tmux session, create session, external sessions, readonly terminal, session roots, heartbeat, sp-webui-dev, sp-engine-dev, writable session

## Scope

- Browser-based terminal backed by tmux and WebSocket
- Tmux session lifecycle: create, attach, kill, cleanup, list
- Terminal history save and retrieval
- Session roots and readonly session enforcement
- Excludes: SSH tunnels (see `cloud-operation` skill → aws-ec2-tunnel action), MCP terminal server (separate MCP)

## Main Behavior

- `GET /api/terminal` returns a WebSocket path for a command or named tmux session
- `GET /api/terminal/tmux/sessions` lists live tmux sessions; external sessions listed separately
- `POST /api/terminal/tmux/create` creates a new named tmux session
- `POST /api/terminal/tmux/kill` kills a session; `POST /api/terminal/tmux/cleanup` removes stale ones
- `GET /api/terminal/tmux/history` and `/saved-histories` serve transcript data
- `DELETE /api/terminal/tmux/saved-history` removes a saved transcript
- `WS /api/terminal/ws` is the live WebSocket endpoint; supports `session=` or `command=` query params
- Readonly flag prevents write access to non-owned sessions

## Code Map

- `core/engine/routes.py` — `/api/terminal*` routes, tmux helpers (`_list_live_tmux_sessions`, `_build_tmux_attach_command_any`, `_validate_writable_session_name`, `_validate_tmux_session_name_any`, `_coerce_command`)
- `core/engine/mcp_servers/terminal/` — MCP server: `main.py`, `terminal.py`, `sessions.py`, `operations.py`, `ssh.py`, `helpers.py`, `constants.py`
- `core/webui/pages/terminal/index.tsx` — terminal page
- `core/webui/pages/terminal-history/` — terminal history page
- `core/webui/pages/terminal-histories/` — saved histories page
- `core/webui/pages/terminals/` — multi-session terminal panel

## Search Commands

```bash
rg "tmux" core/engine/routes.py -n | head -40
rg "api/terminal" core/engine/routes.py -n
rg "tmux" core/engine/mcp_servers/terminal/ -l
rg "TerminalHistory" core/webui/ -l
```

## Related Features

- `core/features/mcp-terminal-server.md`
- `core/features/engine-backend-fastapi.md`

## Update Notes

- Session name validation (`_validate_writable_session_name`) enforces security; do not relax without review
- Readonly mode is enforced server-side; client flag alone is not sufficient
- `sp-webui-dev` and `sp-engine-dev` are reserved session names for dev mode
- Test: `pytest core/engine/tests/` for backend; manual browser test for WebSocket
