---
name: terminal-capture-session-screen
description: "Capture a terminal session screen as text, ansi, or structured output."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "capture_session_screen", "arguments": {}}'
```

## Tool Description
Capture a terminal session screen as text, ansi, or structured output.

## Arguments Schema
```json
{
  "properties": {
    "sessionId": {
      "title": "Sessionid",
      "type": "string"
    },
    "includeScrollback": {
      "default": false,
      "title": "Includescrollback",
      "type": "boolean"
    },
    "format": {
      "default": "text",
      "title": "Format",
      "type": "string"
    }
  },
  "required": [
    "sessionId"
  ],
  "title": "capture_session_screenArguments",
  "type": "object"
}
```
