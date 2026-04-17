# File Realtime Update Issue Notice

## Current Notice

The realtime file update feature is not working reliably yet in File Manager.

User-reported failures still present:

1. A file created from terminal by `touch` does not reliably appear automatically in File Manager.
2. A file updated outside File Manager does not reliably refresh in the open File Manager editor.
3. A file removed from terminal by `rm` does not reliably disappear automatically in File Manager.

## Impact

1. SSE-based realtime update cannot be considered production-ready.
2. Polling fallback currently reduces the visible failure rate, but it does not resolve the root problem.
3. Other WebUI pages should not adopt this realtime mechanism until File Manager behavior is stable.

## Required User-Facing Notice

When realtime degrades, the UI should show a clear notice such as:

`Realtime file sync is degraded. File Manager may require fallback refresh while the issue is being fixed.`

This notice must stay visible instead of silently hiding the problem behind polling.

## Tracking Decision

This issue remains open until all of the following are confirmed:

1. `touch` updates the tree automatically.
2. external edits update the open file automatically when safe.
3. `rm` removes the file automatically.
4. stream health problems are visibly reported in the UI.
