# list_sessions

List terminal sessions currently tracked by this MCP server.

        Use this tool when you need to see which sessions are active and retrieve their session IDs.
        Best for finding an existing session before sending input or capturing its screen.

        Returns:
            JSON object with:
            - sessions: list of session summary objects, each containing sessionId, target, transport, lifecycle, pid, and size.

        Do not use this tool:
            - to list tmux sessions running on the system; use list_tmux_sessions instead

## Usage
```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "list_sessions", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "properties": {},
  "title": "list_sessionsArguments",
  "type": "object"
}
```
