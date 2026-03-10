# Processes

## Brief

Read-oriented monitor for tmux sessions outside the normal Skill Pilot live-session pool.

## User Value

- Helps users inspect long-running or external tmux work from the home view.
- Separates external processes from active user sessions.
- Gives quick visibility into operational state without opening a full terminal page.

## Main Behavior

- Loads external tmux sessions from the home page.
- Refreshes session status when the Processes view is active.
- Lets the user pick an external session to inspect.
- Uses read-only attach behavior for non-owned sessions.

## Related Features

- `new-session.md`
- `live-sessions.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/routes.py`
- Keywords: `fetchExternalSessions`, `activeProcessSession`, `processes`, `externalSessions`
- API routes: `/api/terminal/tmux/external-sessions`, `/api/terminal`
- Helper names: `_list_external_tmux_sessions`, `_build_tmux_attach_command_any`

