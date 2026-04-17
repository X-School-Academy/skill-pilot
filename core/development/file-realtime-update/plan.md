# File Realtime Update Development Plan

## Status

Current state:

1. Initial implementation was completed for file visibility, SSE transport, watcher health reporting, and File Manager fallback polling.
2. The feature is not yet accepted because real-world File Manager behavior is still inconsistent:
   - files created from terminal are not reliably appearing automatically
   - files deleted from terminal are not reliably disappearing automatically
   - files edited from external tools are not reliably refreshing in the open editor
3. This plan is now an active recovery plan for the remaining realtime bug, not just an initial proposal.

## Summary

Add a low-overhead real-time file change channel for file-backed WebUI pages by extending the existing `core/engine` file API with Server-Sent Events and a single shared filesystem watcher. The recommended implementation is:

- backend: one process-level watcher rooted at the repo
- transport: SSE over normal HTTP
- frontend: one lightweight subscription per active page scope
- UI update rule: refresh only the affected directory listing and the currently open file, never the whole page
- visibility rule: File Manager should show hidden files, ignore files, and sensitive filenames such as `config/.env` in the tree, while enforcing read/write permission checks when content access is attempted

This is the best fit for the current stack because:

1. The repo already uses SSE successfully in `dev-swarm`, so the transport pattern is proven here.
2. The engine already exposes file APIs in `core/engine/routes.py`, so the change can stay inside the existing file domain.
3. SSE is cheaper than WebSocket for one-way notifications and avoids polling waste.
4. `watchfiles` is already present in `core/engine/uv.lock`, so we should prefer it over adding `watchdog` unless implementation testing shows a platform-specific blocker.
5. The new requirement is to display dotfiles, ignore files, and `config/.env` in File Manager, so the watcher and list APIs must align with that visibility model instead of suppressing them.

## Final Recommendation

Use `watchfiles` in the Python engine, not `watchdog`, as the default watcher backend.

Reasons:

1. It is already in the engine dependency set, so there is no new package or lockfile churn by default.
2. It is designed for efficient async/server use and is a better fit for FastAPI streaming than periodic polling.
3. It can batch file changes naturally, which helps reduce CPU wakeups and network chatter.

Use SSE, not WebSocket, for the real-time transport.

Reasons:

1. The feature is server-to-client only.
2. Browser `EventSource` is simple and stable.
3. SSE reconnect behavior is built in.
4. It keeps infra and code complexity lower than a bidirectional socket.

Current implementation note:

1. SSE remains the target architecture.
2. Polling fallback is useful as a temporary resilience measure, but it is not the acceptance condition.
3. The remaining work is to make SSE trustworthy enough that fallback becomes a backup path rather than the practical primary path.

Do not make the design depend on HTTP/2 specifically.

Reason:

1. SSE works over standard HTTP semantics already.
2. If a reverse proxy serves HTTP/2, that is a transport optimization, not an application-layer requirement.
3. The application should still work correctly in local dev and direct engine access without an HTTP/2-only assumption.

## Scope

Primary scope:

1. Real-time directory tree refresh for the active path.
2. Real-time file content refresh for the currently open file when it changes outside the current editor session.
3. File Manager visibility updated to include hidden files, ignore files, and `config/.env`, similar to VS Code.
4. Shared backend event stream that other file-based pages can adopt later.

Initial frontend consumer:

1. `core/webui/components/FileManagerContent.tsx`

Follow-up-ready consumers after the base stream exists:

1. Vibe Coding
2. Tasks
3. Workflow/document-driven views
4. Development pages that open and edit repo files through file APIs

## Current-State Review

Relevant existing pieces:

1. `core/engine/routes.py` already owns:
   - `GET /api/files/list`
   - `GET /api/files/read`
   - `POST /api/files/write`
   - file rename/delete/copy/move/mkdir endpoints
2. `core/webui/components/FileManagerContent.tsx` already:
   - caches directory listings
   - loads a selected file on demand
   - autosaves text changes
3. `core/webui/libs/dev-swarm/api.ts` already uses browser `EventSource`, so there is an internal example for SSE wiring.
4. Current `files_list` behavior in `core/engine/routes.py` suppresses dotfiles, so it does not meet the updated File Manager requirement.
5. Current path safety behavior treats sensitive paths as inaccessible, which needs to be split into:
   - list visibility
   - content permission checks

Current gap:

1. There is no push mechanism for file changes.
2. Directory reloads only happen on explicit user actions.
3. Open file content can become stale if files are changed by another tab, another page, git operations, generated outputs, or background agents.
4. Hidden files and ignore files are currently filtered from File Manager listings, which conflicts with the new requirement.

Updated current gap after implementation attempt:

1. The push mechanism exists, but runtime behavior shows it is still not reliable enough.
2. File Manager still needs stronger end-to-end verification against real shell edits from VS Code terminal workflows.
3. The system needs explicit diagnostics to distinguish:
   - SSE unavailable
   - SSE connected but stale
   - watcher unhealthy
   - client-side refresh logic missed a relevant change

## Architecture Decision

### Backend model

Add a shared file-watch service in the engine that:

1. Watches the repo root once per process.
2. Filters noisy and ignored paths before they become events.
3. Batches raw filesystem changes over a short debounce window.
4. Publishes compact normalized change events to active SSE subscribers.

Recommended new module:

- `core/engine/file_realtime.py`

This module should own:

1. watcher lifecycle
2. ignore filtering
3. event normalization
4. subscriber registration
5. per-subscriber scope matching
6. heartbeat generation
7. explicit permission rules for sensitive-path content access

### Transport model

Add one new endpoint:

- `GET /api/files/events`

Suggested query model:

1. `dir=/absolute/repo-relative/path`
2. optional `file=/absolute/repo-relative/path`
3. optional `since=<server revision>`

Behavior:

1. The client reconnects with updated query params when the active directory or open file changes.
2. The backend only emits events relevant to that subscribed scope.
3. The payload includes only metadata, not full file contents or directory snapshots.

### Event contract

Recommended event envelope:

```json
{
  "revision": 42,
  "paths": [
    {
      "path": "/core/development/file-realtime-update/plan.md",
      "kind": "file",
      "change": "modified"
    }
  ],
  "timestamp": 1776038400000
}
```

Recommended change types:

1. `created`
2. `modified`
3. `deleted`
4. `moved`

Rules:

1. One event may include multiple changed paths.
2. Parent directory impact is implied by the changed path.
3. No file body should be sent in SSE events.

## CPU And Network Efficiency Rules

These rules are required for the implementation.

### CPU minimization

1. Use one shared watcher for the repo, not one watcher per client.
2. Filter only truly excluded or high-noise paths before fan-out, not hidden files, ignore files, or `config/.env`.
3. Debounce and coalesce events for a short interval such as `100-250ms`.
4. Reuse one path-normalization and ignore-matching implementation across list/read/watch behavior.
5. Skip only paths that are intentionally blocked or operationally too noisy, plus additional generated directories that should never trigger UI refreshes.

Required exclusion sources for the watcher:

1. directories that are too noisy to watch for UI purposes such as `node_modules`, `.next`, and selected caches
2. paths outside the allowed repo root

Important:

1. Hidden files, ignore files, and `config/.env` should be visible in File Manager and should produce realtime updates.
2. Visibility is separate from content access permission.
3. If a file is listed but cannot be read, the UI should show a clear no-permission state instead of hiding the file.

### Network minimization

1. Send only changed paths and a revision number.
2. Do not push directory listings or file contents over SSE.
3. Do not refetch anything unless the changed path intersects the active directory or open file.
4. Use heartbeat comments or ping events at a low frequency such as `20-30s` only to keep the stream healthy.
5. Reconnect the SSE stream only when the subscribed directory/file scope changes.

### UI minimization

On the frontend:

1. If an event touches the active directory or one of its direct children, refresh only that directory listing.
2. If an event touches the currently open file and the editor is clean, refetch only that file.
3. If an event touches the currently open file and the editor has unsaved local changes, do not overwrite the buffer automatically.
4. Instead, show a non-blocking conflict/reload notice for the user.

## Implementation Phases

### Phase 1: Shared backend watcher service

1. Add a new engine module for process-wide file watching and subscriber fan-out.
2. Use `watchfiles` as the default implementation.
3. Normalize all outgoing event paths to the same leading-slash repo-relative format already used by `/api/files/*`.
4. Replace the current hidden-file suppression model with explicit content-permission checks and high-noise directory filtering.
5. Add event coalescing and revision numbering.

### Phase 2: File Manager visibility update

1. Update `GET /api/files/list` to include hidden files and ignore files.
2. Split path handling into:
   - list-safe path resolution
   - content read/write permission checks
3. Ensure `config/.env` is listed even if read/write is denied by policy or filesystem permissions.
4. Decide whether high-noise directories such as `node_modules` stay visible but lazy-loaded, or remain hidden for usability and performance.
5. Align realtime watcher filtering with the final listing behavior so the tree and stream stay consistent.

### Phase 3: SSE endpoint

1. Add `GET /api/files/events` in `core/engine/routes.py`.
2. Register subscribers by current directory and optional current file.
3. Stream heartbeat messages and compact JSON change events.
4. Cleanly remove subscribers on disconnect.

Additional requirement for the next pass:

1. Emit explicit health/status events, not only comments or silent heartbeats.
2. Provide enough metadata for the frontend to detect stale-but-open streams.

### Phase 4: File Manager frontend integration

1. Add a small reusable SSE helper or hook in `core/webui/libs/` for file events.
2. Subscribe from `core/webui/components/FileManagerContent.tsx` using:
   - current directory
   - open file path when present
3. On relevant change:
   - invalidate and reload the active directory cache only
   - refetch the open file only when safe
4. Preserve current autosave behavior.
5. Avoid update loops for self-originated writes by recognizing the last saved content/path already tracked in the component.

Additional requirement for the next pass:

1. The open file must refresh correctly for editor rename-on-save patterns, not only exact-path modification events.
2. The File Manager must surface realtime health problems visibly instead of silently depending on fallback polling.
3. The final behavior must be verified specifically from external terminal commands such as `touch`, shell edits, and `rm`.

### Phase 5: Shared adoption points

Prepare the stream so other pages can adopt it without a second backend design:

1. Vibe Coding
2. Tasks
3. Workflow editors
4. Development views that bind to repo files

This phase only needs hook readiness in the first implementation, not full page-by-page rollout unless separately approved.

### Phase 6: Verification

1. Validate external file edits update the active directory tree.
2. Validate external file edits update the open file view when there are no unsaved edits.
3. Validate unsaved local edits are not silently overwritten.
4. Validate hidden files and ignore files are listed and updated in real time.
5. Validate `config/.env` is visible in the tree and receives realtime updates.
6. Validate denied content access returns a clear no-permission response without removing the file from the tree.
7. Validate rapid generated changes are coalesced and do not flood the browser.
8. Validate SSE remains the primary update path during normal operation, with fallback used only when the stream is actually degraded.
9. Validate issue notices are visible when the stream becomes unavailable or stale.

## File Change Plan

Expected primary changes:

- `core/engine/routes.py`
- `core/engine/file_realtime.py` (new)
- `core/webui/components/FileManagerContent.tsx`
- `core/webui/libs/file-events.ts` or `core/webui/libs/files/api.ts` helper addition (new or updated)
- backend/frontend tests for the new watcher and SSE flow

Possible secondary changes:

- shared ignore/path helper extraction if `routes.py` and the watcher need the same filtering logic

## Testing Plan

### Backend tests

1. directory listing includes hidden files, ignore files, and `config/.env`
2. watcher emits events for hidden files, ignore files, and `config/.env`
3. content reads on protected files return permission-denied responses without removing those files from listings
4. watcher ignores only configured high-noise exclusions
5. event normalization returns repo-relative leading-slash paths
6. path-scope matching sends only relevant events to a subscriber
7. multiple raw changes are coalesced into one SSE payload window
8. disconnect cleanup removes subscribers cleanly

### Frontend tests

1. directory refresh triggers only when the active directory is affected
2. unrelated file changes do not trigger refetch
3. active open file reloads when clean
4. dirty open file shows conflict state instead of replacing editor contents
5. hidden files, ignore files, and `config/.env` render in the tree
6. protected file opens show a no-permission message
7. EventSource reconnects when the watched directory/file scope changes

### Manual checks

1. edit a file from File Manager in one tab and confirm another tab updates
2. rename, delete, and move files and confirm the tree updates correctly
3. run agent or git-driven file changes and confirm the current visible scope updates without full-page refresh
4. verify dotfiles and ignore files such as `.gitignore` and `.agentignore` appear and update correctly
5. verify `config/.env` appears in the tree
6. verify opening a protected file shows a no-permission message if access is denied

## Open Questions

1. Whether high-noise directories such as `node_modules` should be visible but lazy-loaded, or remain hidden even though normal dotfiles are shown.
2. Whether protected files should be policy-blocked only for write, or for both read and write when the OS permissions would otherwise allow access.
3. Whether the first rollout should remain File Manager-only or also wire Vibe Coding and Tasks in the same implementation batch.
4. Whether move events should be emitted as one `moved` record or as `deleted + created` for simpler client handling.

Resolved implementation direction:

1. Continue File Manager-first until realtime behavior is stable there.
2. Treat the current implementation as incomplete until external shell edits are proven to propagate reliably.

Recommended default:

1. Show hidden files, ignore files, and `config/.env` by default in File Manager.
2. Enforce permission checks when content access is attempted, and surface a no-permission message when denied.
3. Ship File Manager first.
4. Encode rename/move as `deleted + created` internally unless a clean `moved` payload materially simplifies the UI.

## Exit Criteria

This feature is only considered complete when all of the following are true in File Manager:

1. `touch` from terminal makes the new file appear automatically.
2. external file edits refresh the open file automatically when safe.
3. `rm` from terminal removes the file automatically.
4. stream problems are visible to the user as a notice instead of being silently hidden.
