---
name: terminal-tunnel-stop
description: "Stop an active SSH tunnel by tunnel ID."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "tunnel_stop", "arguments": {}}'
```

## Tool Description
Stop an active SSH tunnel by tunnel ID.

## Arguments Schema
```json
{
  "properties": {
    "tunnelId": {
      "title": "Tunnelid",
      "type": "string"
    }
  },
  "required": [
    "tunnelId"
  ],
  "title": "tunnel_stopArguments",
  "type": "object"
}
```
