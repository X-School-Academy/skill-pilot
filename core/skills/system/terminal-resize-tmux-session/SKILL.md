---
name: terminal-resize-tmux-session
description: "Resize a tmux-backed session and return the updated screen snapshot."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "resize_tmux_session", "arguments": {}}'
```

## Tool Description
Resize a tmux-backed session and return the updated screen snapshot.

## Arguments Schema
```json
{
  "properties": {
    "sessionId": {
      "title": "Sessionid",
      "type": "string"
    },
    "cols": {
      "title": "Cols",
      "type": "integer"
    },
    "rows": {
      "title": "Rows",
      "type": "integer"
    }
  },
  "required": [
    "sessionId",
    "cols",
    "rows"
  ],
  "title": "resize_tmux_sessionArguments",
  "type": "object"
}
```
