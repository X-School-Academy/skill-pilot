---
name: terminal-open-session
description: "Start an interactive terminal session and return a session ID."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "open_session", "arguments": {}}'
```

## Tool Description
Start an interactive terminal session and return a session ID.

## Arguments Schema
```json
{
  "properties": {
    "command": {
      "title": "Command",
      "type": "string"
    },
    "args": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Args"
    },
    "target": {
      "default": "local",
      "title": "Target",
      "type": "string"
    },
    "cwd": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Cwd"
    },
    "env": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Env"
    },
    "transport": {
      "default": "auto",
      "title": "Transport",
      "type": "string"
    },
    "lifecycle": {
      "default": "direct",
      "title": "Lifecycle",
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
  "required": [
    "command"
  ],
  "title": "open_sessionArguments",
  "type": "object"
}
```
