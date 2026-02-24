---
name: terminal-exec-command
description: "Run a one-shot shell command on a local or SSH target and return stdout, stderr, and exit code."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "exec_command", "arguments": {}}'
```

## Tool Description
Run a one-shot shell command on a local or SSH target and return stdout, stderr, and exit code.

## Arguments Schema
```json
{
  "properties": {
    "command": {
      "title": "Command",
      "type": "string"
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
    "timeoutMs": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Timeoutms"
    },
    "description": {
      "default": "",
      "title": "Description",
      "type": "string"
    }
  },
  "required": [
    "command"
  ],
  "title": "exec_commandArguments",
  "type": "object"
}
```
