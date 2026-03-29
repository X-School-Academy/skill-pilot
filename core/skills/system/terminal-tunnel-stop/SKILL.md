---
name: terminal-tunnel-stop
description: "Stop an active SSH tunnel by tunnel ID."
---

Use this tool when you need to close a previously established port-forward tunnel.
        Best for cleanup after a task is done or when the forwarded service is no longer needed.

        Args:
            tunnelId: The tunnel ID returned in the result of forward_remote_to_local or forward_local_to_remote.
                      Retrieve it by calling get_operation_status(operationId) and reading result.tunnelId.
                      Example: "tunnel-abc123"

        Returns:
            JSON object with:
            - success: true if the tunnel was stopped
            - message: confirmation message from the SSH pool

        Do not use this tool:
            - to list active tunnels; use tunnel_list instead

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "tunnel_stop", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


## Arguments Schema
```json
{
  "properties": {
    "tunnelId": {
      "title": "Tunnelid",
      "type": "string"
    }
  },
  "required": [
    "tunnelId"
  ],
  "title": "tunnel_stopArguments",
  "type": "object"
}
```
