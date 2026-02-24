# Terminal Session — Dev Plan

## Requirement Reference
`core/development/new-ui-design/terminal-session.md`

---

## Code Review — Gap Analysis

### Current State Summary

| Component | File | Status |
|-----------|------|--------|
| Home page (`/`) | `core/webui/pages/index.tsx` | Exists — has prompt input, Start button, nav menu, tab-based terminal view |
| Terminal page (`/terminal`) | `core/webui/pages/terminal/index.tsx` | Exists — xterm.js + websocket, supports `?command=` and `?session=` params |
| Terminals page (`/terminals`) | `core/webui/pages/terminals/index.tsx` | Exists — lists tmux sessions, Connect/Close buttons, iframe embed |
| Backend routes | `core/engine/routes.py` | Exists — tmux CRUD APIs, websocket terminal, cleanup on beforeunload |
| App wrapper | `core/webui/pages/_app.tsx` | Exists — `beforeunload` fires cleanup beacon to kill ALL `webui-live-*` sessions |

### Gaps Found

#### GAP 1 — Nav Menu Naming (index.tsx + terminals/index.tsx)
- **Requirement**: "New Terminal" → `New Session`; "Terminals" → `Live Sessions`
- **Current**: Still says "New Terminal" and "Terminals" in both pages
- **Action**: Rename labels in both files

#### GAP 2 — "New Session" Nav Behavior (index.tsx)
- **Requirement**: Click `New Session` → redirect to `/`; on `/` the menu item should be grayed/disabled
- **Current**: `New Terminal` directly calls `handleNewTerminal()` which creates a terminal+tab inline
- **Action**: Change `New Session` to navigate to `/` when not already there; disable/gray it when on `/`

#### GAP 3 — Home Page "Start" → iframe Terminal (index.tsx)
- **Requirement**: Click "Start" on `/` should show `/terminal` as an iframe in the main area with the AI agent and prompt as parameters
- **Current**: "Start" creates an inline tab-based terminal view with multiple tabs, manages terminals entirely in React state
- **Action**: Replace the tab-based terminal system. On "Start":
  1. Call backend to create a tmux session with the AI agent CLI + prompt
  2. Show a single `/terminal?session=xxx` iframe in the main content area
  3. The iframe replaces the home view (no tab bar needed)

#### GAP 4 — Tmux Session Creation on "Start" (routes.py)
- **Requirement**: Backend should run the AI agent CLI with prompt in tmux mode, session name `webui-live-xxx`
- **Current**: `_create_webui_tmux_session(command)` already does this — creates `webui-live-{timestamp}-{hex}` and runs the command
- **Status**: ✅ Already implemented. Frontend just needs to call `/api/terminal/tmux/create` with the right command

#### GAP 5 — Session Close: Button (terminal/index.tsx)
- **Requirement**: User can close via a button
- **Current**: Terminal page has a Close/Detach button that sends `{ type: "close" }` over websocket and closes the connection. But it does NOT kill the tmux session — it only detaches
- **Action**: Add a "Close Session" button (or enhance existing) that calls `/api/terminal/tmux/kill` to actually kill the tmux session, not just detach

#### GAP 6 — Session Close: Browser Window Close with 10s Heartbeat (_app.tsx + routes.py)
- **Requirement**: When browser window is closed, kill sessions after 10 seconds; implement heartbeat
- **Current**: `_app.tsx` fires a `sendBeacon` to `/api/terminal/tmux/cleanup` on `beforeunload`, which immediately kills ALL `webui-live-*` sessions. No heartbeat exists.
- **Action**:
  1. **Frontend**: Implement a periodic heartbeat (e.g., every 5s) from the main window to the backend via `POST /api/heartbeat`
  2. **Backend**: Track last heartbeat timestamp. Add a background task that checks: if no heartbeat received for 10s, kill all `webui-live-*` sessions
  3. Remove (or keep as fallback) the `beforeunload` cleanup — it's too aggressive since it kills sessions immediately

#### GAP 7 — Session Close: Before Kill Backend (engine)
- **Requirement**: Clean up tmux sessions before the backend engine process exits
- **Current**: No shutdown hook
- **Action**: Add a FastAPI `shutdown` event handler that calls `_cleanup_webui_tmux_sessions()`

#### GAP 8 — Session Close: Nav Away Releases iframe + WebSocket (index.tsx)
- **Requirement**: If navigating to another screen, release the `/terminal` iframe and close the related websocket
- **Current**: Tab-based view keeps all iframes alive with `display: none` — they are never destroyed
- **Action**: When user navigates away from the active terminal view (clicks another nav item), remove the iframe from DOM entirely (which will cause the websocket inside to close naturally)

#### GAP 9 — "Live Sessions" Route `/terminals` (terminals/index.tsx)
- **Requirement**: Rename to "Live Sessions"
- **Current**: Page title says "Terminals", nav shows "Terminals"
- **Action**: Update title and labels to "Live Sessions"

#### GAP 10 — API Route Names (routes.py)
- **Requirement**: `/api/get-live-sessions`, `/api/close-live-session`
- **Current**: `/api/terminal/tmux/sessions`, `/api/terminal/tmux/kill`
- **Decision**: Keep existing API paths (they are more RESTful and already in use). The requirement was a suggestion for functionality, not strict path naming. Alternatively, add alias routes if strict compliance is needed.
- **Action**: Confirm with user whether to rename or keep existing paths

#### GAP 11 — Clicking "Live Sessions" While Terminal is Showing (terminals/index.tsx)
- **Requirement**: If a terminal iframe is visible and user clicks "Live Sessions" nav, hide/release the terminal (destroy iframe, close websocket)
- **Current**: Clicking "Terminals" nav does nothing special when already on the page
- **Action**: Track whether an iframe is currently displayed. On "Live Sessions" nav click while iframe is shown, set `activeSessionName = null` to unmount the iframe (React key-based iframe will be removed, websocket closes)

#### GAP 12 — Terminal iframe Padding + Auto-Zoom (index.tsx + terminals/index.tsx)
- **Requirement**: Terminal iframe in main panel should have padding on each side and auto-zoom on window resize
- **Current**: iframe is `width: 100%; height: 100%` with no padding
- **Action**: Add CSS padding around the iframe container. The terminal already has a `ResizeObserver` + `window.resize` listener inside `/terminal` that auto-fits, so "auto-zoom" is handled. Just need the padding wrapper.

#### GAP 13 — Empty State for Live Sessions (terminals/index.tsx)
- **Requirement**: If no live sessions, show "No live sessions, create one by clicking New Session"
- **Current**: Shows "No live tmux sessions. Click `New Terminal` in the left menu." — wording needs update
- **Status**: Partially done, just needs text update to match new naming

---

## Implementation Plan

### Phase 1 — Naming & Navigation Changes (Low Risk)

**Task 1.1**: Rename nav items in `index.tsx`
- "New Terminal" → "New Session"
- "Terminals" → "Live Sessions"
- Update route target for "Live Sessions" (already `/terminals`)

**Task 1.2**: Rename nav items and labels in `terminals/index.tsx`
- "New Terminal" → "New Session"
- "Terminals" → "Live Sessions" (active item)
- Page title → "Live Sessions"
- Empty state text → mention "New Session"

**Task 1.3**: "New Session" nav behavior in `index.tsx`
- If current view is not `home`, navigate to `/` (using `router.push('/')`)
- If current view is `home`, gray out / disable the nav item

### Phase 2 — Home Page "Start" → Tmux + iframe (Medium Risk)

**Task 2.1**: Refactor "Start" button handler in `index.tsx`
- On click: call `POST /api/terminal/tmux/create` with `{ command: "<provider> '<prompt>'" }`
- On success: store the returned session name in state
- Switch to a new view (e.g., `activeView = 'live-terminal'`) that renders the iframe

**Task 2.2**: Add `live-terminal` view rendering in `index.tsx`
- Render a padded container with a single iframe: `/terminal?session=<sessionName>`
- Add a "Close Session" button above/beside the iframe
- When closing: call `/api/terminal/tmux/kill`, clear session state, return to `home` view

**Task 2.3**: Remove or simplify the old tab-based terminal system
- Remove `TerminalSession` interface, `terminals` state, tab bar rendering, multi-iframe management
- The `terminals` (ActiveView) case can be removed since we now use `live-terminal` for inline display and `/terminals` page for listing

### Phase 3 — Session Lifecycle (Medium-High Risk)

**Task 3.1**: Heartbeat mechanism — Frontend (`_app.tsx` or new hook)
- In the main window (not iframes), send `POST /api/heartbeat` every 5 seconds
- Skip if `window.self !== window.top` (iframe check already exists)

**Task 3.2**: Heartbeat mechanism — Backend (`routes.py`)
- Add `POST /api/heartbeat` endpoint that updates a global `last_heartbeat_time`
- Add a FastAPI background task (or startup event with `asyncio.create_task`) that periodically checks `last_heartbeat_time`. If stale for >10s, call `_cleanup_webui_tmux_sessions()`

**Task 3.3**: Backend shutdown cleanup
- Add a FastAPI `shutdown` event that calls `_cleanup_webui_tmux_sessions()`
- Location: either in `routes.py` or wherever the FastAPI app is initialized

**Task 3.4**: Nav-away iframe cleanup in `index.tsx`
- When `activeView` changes from `live-terminal` to anything else, remove the iframe from DOM
- The iframe removal triggers websocket close inside `/terminal` page naturally
- Optionally call `/api/terminal/tmux/kill` if user wants to end the session (vs just hide)

**Task 3.5**: Update `_app.tsx` `beforeunload` handler
- Keep the `sendBeacon` cleanup as a best-effort fallback
- The heartbeat timeout (Task 3.2) is the primary mechanism now

### Phase 4 — Live Sessions Page Improvements (Low Risk)

**Task 4.1**: Toggle iframe on "Live Sessions" nav click in `terminals/index.tsx`
- If `activeSessionName` is set (iframe is showing), set it to `null` to unmount iframe
- If no iframe is showing, keep current behavior (show session list)

**Task 4.2**: Add padding to terminal iframe containers
- In `index.tsx` (the new live-terminal view): wrap iframe in a container with padding (e.g., 12-16px)
- In `terminals/index.tsx`: add padding around the iframe area
- The xterm auto-fit inside the iframe handles resize automatically

### Phase 5 — Close Session Button in /terminal Page (Low Risk)

**Task 5.1**: Enhance Close/Detach in `terminal/index.tsx`
- When in session mode (`?session=xxx`): add a "Kill Session" option that calls `/api/terminal/tmux/kill` before closing the websocket
- Current "Detach" button just closes the websocket — keep this as-is for the iframe use case (parent manages lifecycle)

---

## File Change Summary

| File | Changes |
|------|---------|
| `core/webui/pages/index.tsx` | Rename nav items, refactor Start→tmux+iframe, add live-terminal view, remove tab system, nav-away cleanup |
| `core/webui/pages/terminals/index.tsx` | Rename labels, toggle iframe on nav click, add iframe padding, update empty state text |
| `core/webui/pages/terminal/index.tsx` | Minor: add optional kill-session button for session mode |
| `core/webui/pages/_app.tsx` | Add heartbeat interval, keep beforeunload as fallback |
| `core/engine/routes.py` | Add `/api/heartbeat` endpoint, heartbeat timeout watcher, shutdown cleanup hook |

## Design Decisions (Confirmed)

1. **API paths**: Keep current RESTful paths (`/api/terminal/tmux/sessions`, `/api/terminal/tmux/kill`) — no rename
2. **Nav-away behavior**: Just detach — session survives and remains visible in Live Sessions
3. **Start button**: Always create a new tmux session (that's why it's called "New Session")
