---
name: terminal-open-session
description: "Start an interactive local or remote SSH terminal session and return a session ID."
---

Use this tool when you need to run a long-running or interactive process such as a shell, REPL, or server.
        Best for processes that produce output over time or require ongoing input.

        Args:
            command: The executable to run. Required.
                     Examples: "bash", "python3", "node", "ssh prod -t bash"
                     For SSH via local tmux (Method 2 / fast): use "ssh prod -t 'bash'" with target="local".
            args: Optional list of arguments to pass to the command.
                  Example: ["-i", "--verbose"]
            target: Where to run the session.
                     - "local" — run on the local machine (default). Also use this for local tmux wrapping an SSH command.
                     - "ssh:<profile>" — run directly on a remote SSH host, e.g. "ssh:prod", "ssh:dev".
                       Profiles are defined in the server's SSH config file (config.json).
            cwd: Working directory for the session. Example: "/app"
            env: Additional environment variables. Example: {"RAILS_ENV": "production"}
            transport: I/O transport mode.
                     - "auto" — automatically picks pty for interactive CLIs, pipe otherwise (default, recommended)
                     - "pty" — force pseudo-terminal; use for interactive programs (vim, python REPL, bash prompts)
                     - "pipe" — force stdin/stdout/stderr pipes; use for non-interactive scripts
            lifecycle: Session lifecycle mode.
                     - "direct" — run process directly in the foreground (default)
                     - "tmux" — wrap in a tmux session; survives agent disconnection; required for long-running background tasks
            cols: Terminal width in columns. Must be between 10 and 500. Default: 80.
            rows: Terminal height in rows. Must be between 5 and 200. Default: 24.

        Returns:
            JSON object with:
            - sessionId: unique ID used for all subsequent session operations (send_session_input, capture_session_screen, etc.)
            - target: the target used
            - pid: process ID of the started process
            - cols: actual terminal width
            - rows: actual terminal height
            - transport: transport mode in use
            - lifecycle: lifecycle mode in use
            - initialScreen: text snapshot of the terminal screen after startup

        Do not use this tool:
            - for simple one-shot commands; use exec_command instead
            - when sudo is needed for a one-shot command; use sudo_exec_command instead

        Notes:
            - Use send_session_input to send input and capture_session_screen to read output.
            - Use lifecycle="tmux" for background tasks that must survive agent disconnection.
            - For high-frequency interactions with remote hosts, prefer target="local" with command="ssh <profile> -t bash" and lifecycle="tmux" (Method 2 — 10x faster than target="ssh:<profile>").
            - Always terminate or detach sessions when done to avoid resource leaks.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "open_session", "arguments": {}}'
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
