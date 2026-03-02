---
name: terminal-detach-tmux-session
description: "Detach MCP from a tmux-backed session while keeping the tmux workload running."
---

Use this tool when you want to stop monitoring a tmux session without killing the underlying process.
        Best for background tasks that should continue running after the agent disconnects.

        Args:
            sessionId: ID of the MCP-tracked tmux session to detach. Must have been opened with lifecycle="tmux".
                       Use list_sessions to find active session IDs.
                       Example: "sess-abc123"

        Returns:
            JSON object with:
            - success: true if detach succeeded
            - action: "detach"
            - exitCode: exit code of the MCP wrapper process
            - signal: signal used to stop the wrapper (if any)

        Do not use this tool:
            - to stop the underlying process entirely; use terminate_session instead
            - on non-tmux sessions; only lifecycle="tmux" sessions can be detached
            - to re-attach later; use attach_tmux_session with the original tmux session name

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "detach_tmux_session", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "sessionId": {
      "title": "Sessionid",
      "type": "string"
    }
  },
  "required": [
    "sessionId"
  ],
  "title": "detach_tmux_sessionArguments",
  "type": "object"
}
```
