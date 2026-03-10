# Live Sessions

## Brief

Session browser for active tmux-backed agent terminals, including create, attach, open, and close operations.

## User Value

- Shows all live agent sessions in one place.
- Makes it easy to reconnect to prior work.
- Supports both WebUI-attached and native terminal session flows.

## Main Behavior

- Lists active tmux sessions and their metadata.
- Creates new tmux-backed sessions from a command.
- Opens a session through the terminal WebSocket or native terminal attach flow.
- Supports session kill and cleanup behavior.
- Separates live sessions from external tmux processes.

## Related Features

- `platform-shell-and-navigation.md`
- `new-session.md`
- `processes.md`
- `workflows.md`

## Code References

- `core/webui/pages/terminals/index.tsx`
- `core/engine/routes.py`
- Keywords: `TerminalsPage`, `createTmuxSession`, `busyAction`, `terminal/tmux/sessions`, `terminal/tmux/create`, `terminal/tmux/kill`, `terminal/ws`
- Helper names: `_list_live_tmux_sessions`, `_create_webui_tmux_session`, `_create_native_tmux_session`, `_open_native_terminal_for_tmux`, `_cleanup_webui_tmux_sessions`

