---
name: terminal-list-sessions
description: "List terminal sessions currently tracked by this MCP server."
---

Use this tool when you need to see which sessions are active and retrieve their session IDs.
        Best for finding an existing session before sending input or capturing its screen.

        Returns:
            JSON object with:
            - sessions: list of session summary objects, each containing sessionId, target, transport, lifecycle, pid, and size.

        Do not use this tool:
            - to list tmux sessions running on the system; use list_tmux_sessions instead

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "list_sessions", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {},
  "title": "list_sessionsArguments",
  "type": "object"
}
```
