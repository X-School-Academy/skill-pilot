---
name: terminal-forward-remote-to-local
description: "Start an SSH local port-forward from localPort to remoteHost:remotePort."
---

Use this tool when you need to access a service on a remote network through an SSH tunnel.
        Best for reaching databases, internal APIs, or other services behind an SSH gateway.
        Equivalent to: ssh -L localPort:remoteHost:remotePort <target>

        Args:
            target: SSH profile identifying the tunnel endpoint. Must be "ssh:<profile>" (e.g. "ssh:prod", "ssh:dev").
                    Profiles are defined in the server's SSH config file (config.json).
            remoteHost: Hostname or IP of the service to reach on the remote network.
                        Use "localhost" to reach a service running on the SSH host itself.
                        Example: "localhost", "db.internal", "10.0.1.5"
            remotePort: Port of the remote service. Must be in range 1..65535.
                        Example: 5432 for PostgreSQL, 3306 for MySQL, 6379 for Redis.
            localPort: Local port to bind. Use 0 to let the OS assign an available port.
                       Example: 5432 to bind locally on the same port, 0 for auto-assign.

        Returns:
            JSON object with:
            - accepted: true when the tunnel operation has been queued
            - operationId: ID to track tunnel status via get_operation_status
            - status: initial operation status
            - target: the SSH target used

        Do not use this tool:
            - to expose a local service on a remote host; use forward_local_to_remote instead
            - to stop a tunnel; use tunnel_stop instead
            - with target="local"; this tool only supports SSH targets

        Notes:
            - The tunnel is established asynchronously. Poll get_operation_status for tunnelId and localAddress.
            - If localPort is 0, the actual assigned port is returned in the operation result as localAddress.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "forward_remote_to_local", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


## Arguments Schema
```json
{
  "properties": {
    "target": {
      "title": "Target",
      "type": "string"
    },
    "remoteHost": {
      "title": "Remotehost",
      "type": "string"
    },
    "remotePort": {
      "title": "Remoteport",
      "type": "integer"
    },
    "localPort": {
      "default": 0,
      "title": "Localport",
      "type": "integer"
    }
  },
  "required": [
    "target",
    "remoteHost",
    "remotePort"
  ],
  "title": "forward_remote_to_localArguments",
  "type": "object"
}
```
