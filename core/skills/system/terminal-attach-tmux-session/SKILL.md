---
name: terminal-attach-tmux-session
description: "Attach MCP control to an existing tmux session or pane."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "attach_tmux_session", "arguments": {}}'
```

## Tool Description
Attach MCP control to an existing tmux session or pane.

## Arguments Schema
```json
{
  "properties": {
    "sessionRef": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Sessionref"
    },
    "paneRef": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Paneref"
    },
    "target": {
      "default": "local",
      "title": "Target",
      "type": "string"
    },
    "cols": {
      "default": 80,
      "title": "Cols",
      "type": "integer"
    },
    "rows": {
      "default": 24,
      "title": "Rows",
      "type": "integer"
    }
  },
  "title": "attach_tmux_sessionArguments",
  "type": "object"
}
```
