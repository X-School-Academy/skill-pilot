---
name: terminal-get-operation-status
description: "Get status for an async SCP or tunnel operation by operation ID."
---

Use this tool when you need to check if an asynchronous file transfer or tunnel setup has completed.
        Best for polling after scp_upload, scp_download, forward_remote_to_local, or forward_local_to_remote.

        Args:
            operationId: The operation ID returned in the accepted response of the async operation.
                         Example: "op-abc123" (from scp_upload, scp_download, forward_remote_to_local, or forward_local_to_remote)

        Returns:
            JSON object with:
            - operationId: the operation ID
            - status: current status — "pending", "running", "succeeded", or "failed"
            - result: result data when succeeded. For SCP: {localPath, remotePath, message}. For tunnels: {tunnelId, localAddress, remoteAddress}.
            - error: error message string when status is "failed"
            - tunnel: live tunnel info object if the operation created a tunnel (includes tunnelId)

        Notes:
            - Poll periodically (e.g. every 1–2 seconds) until status is "succeeded" or "failed".
            - For tunnel operations, read result.tunnelId then pass it to tunnel_stop when done.
            - For SCP operations, result.message contains a human-readable completion summary.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "get_operation_status", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "operationId": {
      "title": "Operationid",
      "type": "string"
    }
  },
  "required": [
    "operationId"
  ],
  "title": "get_operation_statusArguments",
  "type": "object"
}
```
