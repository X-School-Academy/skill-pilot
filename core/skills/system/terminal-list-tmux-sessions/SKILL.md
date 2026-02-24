---
name: terminal-list-tmux-sessions
description: "List tmux sessions on a local or SSH target."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "list_tmux_sessions", "arguments": {}}'
```

## Tool Description
List tmux sessions on a local or SSH target.

## Arguments Schema
```json
{
  "properties": {
    "target": {
      "default": "local",
      "title": "Target",
      "type": "string"
    }
  },
  "title": "list_tmux_sessionsArguments",
  "type": "object"
}
```
