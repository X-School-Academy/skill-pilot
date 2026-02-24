---
name: terminal-sudo-exec-command
description: "Run a shell command with sudo privileges on a local or SSH target."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "sudo_exec_command", "arguments": {}}'
```

## Tool Description
Run a shell command with sudo privileges on a local or SSH target.

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
  "title": "sudo_exec_commandArguments",
  "type": "object"
}
```
