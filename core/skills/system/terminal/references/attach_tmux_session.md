# attach_tmux_session

Attach MCP control to an existing tmux session or pane.

        Use this tool when you need to interact with a tmux session already running on the system.
        Best for reconnecting to background processes or long-running tasks started outside this MCP server.

        Args:
            sessionRef: Name of the tmux session to attach. Provide either sessionRef or paneRef, not both.
                        Use the session name as shown by list_tmux_sessions or `tmux ls`.
                        Example: "work", "training", "mcp-abc123"
                        When using sessionRef, MCP attaches to pane 0 of window 0 by default (session:0.0).
            paneRef: Tmux pane reference to attach to a specific pane. Provide either paneRef or sessionRef.
                     Format: "<session>:<window>.<pane>" — e.g. "work:0.1", "training:1.0"
                     Use this when you need to target a pane other than the default (0.0).
            target: Where the tmux session is running.
                     - "local" — the local machine (default)
                     - "ssh:<profile>" — a remote SSH host, e.g. "ssh:prod", "ssh:dev"
                       Profiles are defined in the server's SSH config file (config.json).
            cols: Terminal width in columns. Must be between 10 and 500. Default: 80.
            rows: Terminal height in rows. Must be between 5 and 200. Default: 24.

        Returns:
            JSON object with:
            - sessionId: MCP session ID for subsequent operations (send_session_input, capture_session_screen, etc.)
            - target, transport, lifecycle: session metadata
            - pid: process ID
            - cols, rows: terminal dimensions in use
            - sessionRef: the session name used (if provided)
            - paneRef: the pane reference used (if provided)
            - initialScreen: text snapshot of the terminal after attaching

        Do not use this tool:
            - to create a new session from scratch; use open_session instead
            - to discover available tmux sessions first; use list_tmux_sessions

## Usage
```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "attach_tmux_session", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "properties": {
    "sessionRef": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Sessionref"
    },
    "paneRef": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Paneref"
    },
    "target": {
      "default": "local",
      "title": "Target",
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
  "title": "attach_tmux_sessionArguments",
  "type": "object"
}
```
