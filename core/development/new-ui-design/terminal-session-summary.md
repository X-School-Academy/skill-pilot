# Terminal Session — Implementation Summary

**Status**: All 5 phases completed.

## Files Changed

### `core/webui/pages/index.tsx` — Major refactor
- Renamed nav: "New Terminal" → "New Session" (disabled/grayed on `/`), "Terminals" → "Live Sessions"
- Removed old tab-based terminal system (`TerminalSession` interface, `terminals` state, tab bar, multi-iframe management, `CloseButton` import)
- "Start" now calls `POST /api/terminal/tmux/create` with AI agent + prompt, then shows `/terminal?session=xxx` iframe
- New `live-terminal` ActiveView with session info bar, Detach button, and padded iframe (12px, border-radius 8)
- Nav-away from `live-terminal` clears `liveSessionName` → iframe unmounts → websocket closes naturally (detach, not kill)
- Added `startingSession` loading state on Start button

### `core/webui/pages/terminals/index.tsx` — Labels + UX
- Renamed: "New Terminal" → "New Session" (navigates to `/`), "Terminals" → "Live Sessions"
- Page title → "Skill Pilot - Live Sessions"
- Session list header → "Live Sessions"
- Empty state → "No live sessions. Click "New Session" to create one."
- Clicking "Live Sessions" nav while iframe is visible toggles it off (`activeSessionName = null`)
- Added 12px padding + border-radius 8 around terminal iframe
- Removed unused `handleNewTerminal` function

### `core/webui/pages/terminal/index.tsx` — Kill session button
- Added `handleKillSession()` — calls `POST /api/terminal/tmux/kill` then closes websocket
- Session mode now shows two buttons: "Kill Session" (red) and "Detach" (gray)
- Non-session mode still shows single "Close" button

### `core/webui/pages/_app.tsx` — Heartbeat
- Added heartbeat: `POST /api/heartbeat` every 5 seconds from main window (skips iframes)
- Kept `beforeunload` → `sendBeacon` cleanup as fallback

### `core/engine/routes.py` — Heartbeat backend
- Added `POST /api/heartbeat` endpoint updating `_last_heartbeat_time`
- Added `_heartbeat_watcher()` async task: checks every 5s, cleans up all `webui-live-*` tmux sessions if no heartbeat for 10s
- Exposed `start_heartbeat_watcher()` for app startup

### `core/engine/app_factory.py` — Startup/shutdown hooks
- Startup: starts heartbeat watcher via `start_heartbeat_watcher()`
- Shutdown: calls `_cleanup_webui_tmux_sessions()` to clean up tmux sessions before engine exits

## Design Decisions

1. **API paths**: Keep current RESTful paths (`/api/terminal/tmux/sessions`, `/api/terminal/tmux/kill`) — no rename
2. **Nav-away behavior**: Just detach — session survives and remains visible in Live Sessions
3. **Start button**: Always create a new tmux session (that's why it's called "New Session")
