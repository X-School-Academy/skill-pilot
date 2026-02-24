---
name: terminal-send-session-input
description: "Send text or a special key to a session and return the updated screen snapshot."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "send_session_input", "arguments": {}}'
```

## Tool Description
Send text or a special key to a session and return the updated screen snapshot.

## Arguments Schema
```json
{
  "properties": {
    "sessionId": {
      "title": "Sessionid",
      "type": "string"
    },
    "input": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Input"
    },
    "specialKey": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Specialkey"
    },
    "waitMs": {
      "default": 100,
      "title": "Waitms",
      "type": "integer"
    }
  },
  "required": [
    "sessionId"
  ],
  "title": "send_session_inputArguments",
  "type": "object"
}
```
