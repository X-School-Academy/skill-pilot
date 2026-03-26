---
name: terminal-sudo-exec-command
description: "Run a shell command with sudo privileges on a local or SSH target."
---

Use this tool when you need to execute a command requiring elevated privileges.
        Best for system administration tasks such as package installation or service management.

        Args:
            command: The shell command to run with sudo. Maximum 2000 characters for local; SSH profile maxChars applies for remote.
                     Examples: "systemctl restart nginx", "apt install -y curl", "chmod 600 /etc/secret"
            target: Where to run the command.
                     - "local" — run on the local machine (default)
                     - "ssh:<profile>" — run on a remote SSH host, e.g. "ssh:prod", "ssh:dev"
            cwd: Working directory for the command. Defaults to the current working directory.
            env: Additional environment variables to merge into the process environment.
                 Example: {"DEBIAN_FRONTEND": "noninteractive"}
            timeoutMs: Timeout in milliseconds. Must be greater than 0 if provided.
                       Example: 60000 for a 60-second timeout.
            description: Human-readable label appended as a comment in the command string for audit trails.

        Returns:
            JSON object with:
            - target: the target used
            - success: true if exit code is 0
            - exitCode: integer exit code
            - stdout: captured standard output
            - stderr: captured standard error

        Do not use this tool:
            - when sudo access is not required; use exec_command instead
            - to start interactive sessions; use open_session instead

        Notes:
            - Requires passwordless sudo configured on the target machine (sudo -n).
            - For SSH targets, set sudoPassword in the SSH profile if the host requires a password.
            - Local commands are wrapped with sudo -n sh -c before execution.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "sudo_exec_command", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


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
