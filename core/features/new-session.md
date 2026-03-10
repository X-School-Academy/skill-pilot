# New Session

## Brief

Home screen entry flow for starting a new AI agent session, optionally tied to a workflow and feature-level security settings.

## User Value

- Lets users start work from one prompt box.
- Supports workflow-backed sessions without leaving the home screen.
- Applies session safety settings before launch.

## Main Behavior

- Accepts a free-form prompt for a new session.
- Supports provider selection, workflow selection, resume flags, and next-node trigger behavior.
- Applies sandbox, auto-approve, and network toggles from saved security settings.
- Can launch sessions into the WebUI terminal flow or native terminal flow.
- Shares the same home route that also hosts inline operational views via `?view=...`.

## Related Features

- `platform-shell-and-navigation.md`
- `live-sessions.md`
- `workflows.md`
- `ai-and-security.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/routes.py`
- Keywords: `new_session`, `startingSession`, `newSessionWorkflow`, `newSessionSandbox`, `newSessionAuto`, `newSessionNetwork`, `workflowExecuteStatus`
- API routes: `/api/terminal/tmux/create`, `/api/config/settings`, `/api/workflows/execute/status`

