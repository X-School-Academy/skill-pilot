---
name: terminal-resize-tmux-session
description: "Resize a tmux-backed session and return the updated screen snapshot."
---

Use this tool when you need to change the terminal dimensions of a tmux session.
        Best for adjusting the viewport before capturing output or when the display appears malformed.

        Args:
            sessionId: ID of the tmux session returned by open_session (with lifecycle="tmux") or attach_tmux_session.
                       Example: "sess-abc123"
            cols: New terminal width in columns. Must be between 10 and 500.
                  Example: 220 for a wide terminal, 80 for standard width.
            rows: New terminal height in rows. Must be between 5 and 200.
                  Example: 50 for tall output, 24 for standard height.

        Returns:
            JSON object with:
            - success: true if resize succeeded
            - target, transport, lifecycle: session metadata
            - previousSize: {cols, rows} before the resize
            - newSize: {cols, rows} after the resize
            - screen: text snapshot of the terminal after the resize

        Do not use this tool:
            - on non-tmux sessions; this tool only supports lifecycle="tmux" sessions

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "resize_tmux_session", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


## Arguments Schema
```json
{
  "properties": {
    "sessionId": {
      "title": "Sessionid",
      "type": "string"
    },
    "cols": {
      "title": "Cols",
      "type": "integer"
    },
    "rows": {
      "title": "Rows",
      "type": "integer"
    }
  },
  "required": [
    "sessionId",
    "cols",
    "rows"
  ],
  "title": "resize_tmux_sessionArguments",
  "type": "object"
}
```
