---
name: terminal-list-tmux-sessions
description: "List tmux sessions on a local or SSH target."
---

Use this tool when you need to enumerate existing tmux sessions running on the system.
        Best for discovering named tmux sessions before attaching to them with attach_tmux_session.

        Args:
            target: Where to query for tmux sessions.
                     - "local" — list tmux sessions on the local machine (default)
                     - "ssh:<profile>" — list tmux sessions on a remote SSH host, e.g. "ssh:prod", "ssh:dev"
                       Profiles are defined in the server's SSH config file (config.json).

        Returns:
            JSON object with:
            - target: the target queried
            - tmuxSessions: list of tmux session descriptors (name, windows, created, attached status, etc.)

        Do not use this tool:
            - to list MCP-tracked sessions; use list_sessions instead
            - to attach to a tmux session; use attach_tmux_session instead

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "list_tmux_sessions", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "target": {
      "default": "local",
      "title": "Target",
      "type": "string"
    }
  },
  "title": "list_tmux_sessionsArguments",
  "type": "object"
}
```
