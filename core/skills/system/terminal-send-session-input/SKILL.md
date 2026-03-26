---
name: terminal-send-session-input
description: "Send text or a special key to a session and return the updated screen snapshot."
---

Use this tool when you need to interact with a running terminal session by typing text or pressing keys.
        Best for driving interactive programs such as shells, REPLs, menus, or prompts.

        Args:
            sessionId: ID of the session returned by open_session or attach_tmux_session.
                       Example: "sess-abc123"
            input: Text string to write to the terminal. Provide either input or specialKey, not both.
                   To run a shell command, append a newline: "ls -la
", "cd /app
", "exit
"
                   To type text without submitting: "hello world" (no newline)
            specialKey: Named key to send instead of text. Provide either specialKey or input, not both.
                        Supported values: "Enter", "Tab", "Escape", "Backspace", "Delete",
                        "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
                        "Ctrl-C" (interrupt), "Ctrl-D" (EOF/logout), "Ctrl-Z" (suspend),
                        "shift+ArrowUp", "alt+ArrowLeft", "ctrl+ArrowRight"
            waitMs: Milliseconds to wait after sending input before capturing the screen.
                    Must be between 0 and 10000. Default: 100.
                    Increase for slow commands: 500–2000ms. Use 0 for instant capture.

        Returns:
            JSON object with:
            - success: true if input was delivered
            - target: the session target
            - transport: transport mode in use
            - lifecycle: lifecycle mode in use
            - screen: text snapshot of the terminal after waiting
            - cursorPosition: current cursor position as {row, col}

        Do not use this tool:
            - to read the screen without sending input; use capture_session_screen instead
            - for one-shot commands that do not need interaction; use exec_command instead

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "send_session_input", "arguments": {}}'
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
    "input": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Input"
    },
    "specialKey": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Specialkey"
    },
    "waitMs": {
      "default": 100,
      "title": "Waitms",
      "type": "integer"
    }
  },
  "required": [
    "sessionId"
  ],
  "title": "send_session_inputArguments",
  "type": "object"
}
```
