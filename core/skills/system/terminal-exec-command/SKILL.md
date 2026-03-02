---
name: terminal-exec-command
description: "Run a one-shot shell command on a local or SSH target and return stdout, stderr, and exit code."
---

Use this tool when you need to execute a shell command and capture its output.
        Best for short-lived commands that complete within the timeout window.

        Args:
            command: The shell command to run. Maximum 2000 characters for local; SSH profile maxChars applies for remote.
                     Examples: "ls -la /app", "docker ps", "cat /etc/os-release"
            target: Where to run the command.
                     - "local" — run on the local machine (default)
                     - "ssh:<profile>" — run on a remote SSH host defined in config.json, e.g. "ssh:prod", "ssh:dev"
            cwd: Working directory for the command. Defaults to the current working directory.
                 Example: "/app" or "/home/deploy"
            env: Additional environment variables to merge into the process environment.
                 Example: {"DEBUG": "1", "PORT": "8080"}
            timeoutMs: Timeout in milliseconds. Must be greater than 0 if provided.
                       Example: 30000 for a 30-second timeout.
            description: Human-readable label appended as a comment in the command string for audit trails.
                         Example: "check disk usage"

        Returns:
            JSON object with:
            - target: the target used
            - success: true if exit code is 0
            - exitCode: integer exit code
            - stdout: captured standard output
            - stderr: captured standard error

        Do not use this tool:
            - to start long-running or interactive processes; use open_session instead
            - when sudo access is required; use sudo_exec_command instead

        Notes:
            - Local commands run via /bin/bash with shell=True.
            - SSH commands are wrapped with cwd and env handling before execution.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "exec_command", "arguments": {}}'
```

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
