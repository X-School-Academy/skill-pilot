# terminate_session

Terminate a terminal session by ID and remove it from MCP tracking.

        Use this tool when you are done with a terminal session and want to stop its process.
        Best for cleanup after a task completes or when a session becomes unresponsive.

        Args:
            sessionId: ID of the session to terminate. Use list_sessions to find active session IDs.
                       Example: "sess-abc123"
            signal: Signal to send to the process. Default: "SIGTERM".
                     - "SIGTERM" — graceful shutdown; gives the process time to clean up (recommended)
                     - "SIGKILL" — force kill immediately; use when SIGTERM does not stop the process
                     - "SIGHUP" — hangup; simulates a terminal disconnect (useful for daemons that reload on SIGHUP)

        Returns:
            JSON object with:
            - success: true if termination succeeded
            - action: "terminate"
            - exitCode: exit code after termination
            - signal: signal used to terminate

        Do not use this tool:
            - when you want to keep the tmux process running in the background; use detach_tmux_session instead
            - to list sessions; use list_sessions instead

## Usage
```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "terminate_session", "arguments": {}}'
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
    "signal": {
      "default": "SIGTERM",
      "title": "Signal",
      "type": "string"
    }
  },
  "required": [
    "sessionId"
  ],
  "title": "terminate_sessionArguments",
  "type": "object"
}
```
