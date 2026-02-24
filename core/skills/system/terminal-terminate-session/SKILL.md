---
name: terminal-terminate-session
description: "Terminate a terminal session by ID and remove it from MCP tracking."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "terminate_session", "arguments": {}}'
```

## Tool Description
Terminate a terminal session by ID and remove it from MCP tracking.

## Arguments Schema
```json
{
  "properties": {
    "sessionId": {
      "title": "Sessionid",
      "type": "string"
    },
    "signal": {
      "default": "SIGTERM",
      "title": "Signal",
      "type": "string"
    }
  },
  "required": [
    "sessionId"
  ],
  "title": "terminate_sessionArguments",
  "type": "object"
}
```
