---
name: terminal-detach-tmux-session
description: "Detach MCP from a tmux-backed session while keeping the tmux workload running."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "detach_tmux_session", "arguments": {}}'
```

## Tool Description
Detach MCP from a tmux-backed session while keeping the tmux workload running.

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
