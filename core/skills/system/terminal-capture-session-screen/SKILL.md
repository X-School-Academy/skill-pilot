---
name: terminal-capture-session-screen
description: "Capture a terminal session screen as text, ansi, or structured output."
---

Use this tool when you need to read the current output of a running terminal session.
        Best for polling a session for results, checking prompts, or extracting structured data.

        Args:
            sessionId: ID of the session returned by open_session or attach_tmux_session.
                       Example: "sess-abc123"
            includeScrollback: If true, include scrollback buffer content above the visible screen area.
                               Default: false. Set to true to read command history or output that has scrolled off.
            format: Output format. Default: "text".
                     - "text" — plain text content of the visible screen (recommended for most use cases)
                     - "ansi" — raw ANSI escape sequences; use when color/style information is needed
                     - "structured" — full metadata object with cursor position, terminal size, and session info; also accepts "detailed" as an alias

        Returns:
            For "text" format, JSON object with:
            - screen: visible terminal text
            - cursorPosition: current cursor position as {row, col}
            - terminalSize: {cols, rows}
            - target, transport, lifecycle: session metadata
            For "ansi" format, JSON object with:
            - ansiData: raw ANSI-encoded terminal content
            For "structured" format, full snapshot dict with target, transport, and lifecycle fields added.

        Do not use this tool:
            - to send input to the session; use send_session_input instead

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "capture_session_screen", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "sessionId": {
      "title": "Sessionid",
      "type": "string"
    },
    "includeScrollback": {
      "default": false,
      "title": "Includescrollback",
      "type": "boolean"
    },
    "format": {
      "default": "text",
      "title": "Format",
      "type": "string"
    }
  },
  "required": [
    "sessionId"
  ],
  "title": "capture_session_screenArguments",
  "type": "object"
}
```
