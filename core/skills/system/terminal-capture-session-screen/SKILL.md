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
                               Default: false. For tmux sessions this captures the full pane history (`tmux capture-pane -S -`).
            joinWrappedLines: If true, join terminal-wrapped lines into logical lines when supported by the backend.
                              Default: true. For tmux sessions this maps to `tmux capture-pane -J`, which is useful for
                              reading long messages without resizing the pane. Set to false to preserve width-based wrapping.
            captureStart: Optional tmux capture start bound. Accepts "-" or an integer string such as "-200" or "0".
                          Examples:
                          - None: use the visible pane start unless includeScrollback is true
                          - "-200": start 200 history lines above the visible pane
                          - "-": start from the beginning of history
                          When set, this takes precedence over includeScrollback for tmux sessions.
            captureEnd: Optional tmux capture end bound. Accepts "-" or an integer string such as "0" or "15".
                        Examples:
                        - None: use tmux's default end point
                        - "-": end at the bottom of the visible pane
                        - "15": end at pane line 15
                        Supported only for tmux sessions.
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
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


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
    "joinWrappedLines": {
      "default": true,
      "title": "Joinwrappedlines",
      "type": "boolean"
    },
    "captureStart": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Capturestart"
    },
    "captureEnd": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Captureend"
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
