---
name: terminal-forward-local-to-remote
description: "Start an SSH remote port-forward from remotePort to localHost:localPort."
---

Use this tool when you need to expose a local service on a remote SSH host's port.
        Best for making a locally running service accessible from a remote machine.
        Equivalent to: ssh -R remotePort:localHost:localPort <target>

        Args:
            target: SSH profile identifying the tunnel endpoint. Must be "ssh:<profile>" (e.g. "ssh:prod", "ssh:dev").
                    Profiles are defined in the server's SSH config file (config.json).
            localHost: Hostname or IP of the local service to expose.
                       Use "localhost" to expose a service running on the local machine.
                       Example: "localhost", "127.0.0.1"
            localPort: Port of the local service. Must be in range 1..65535.
                       Example: 8080 for a local web server, 3000 for a dev server.
            remotePort: Port to bind on the remote host. Use 0 to let the OS assign a port.
                        Example: 9000 to expose as port 9000 on the remote machine.
            remoteHost: Interface to bind on the remote host. Defaults to "127.0.0.1" (loopback only).
                        Use "0.0.0.0" to expose on all remote interfaces (requires GatewayPorts on SSH server).

        Returns:
            JSON object with:
            - accepted: true when the tunnel operation has been queued
            - operationId: ID to track tunnel status via get_operation_status
            - status: initial operation status
            - target: the SSH target used

        Do not use this tool:
            - to access a remote service locally; use forward_remote_to_local instead
            - to stop a tunnel; use tunnel_stop instead
            - with target="local"; this tool only supports SSH targets

        Notes:
            - The tunnel is established asynchronously. Poll get_operation_status for tunnelId and remoteAddress.
            - If remotePort is 0, the actual assigned port is returned in the operation result as remoteAddress.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "forward_local_to_remote", "arguments": {}}'
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
    "localHost": {
      "title": "Localhost",
      "type": "string"
    },
    "localPort": {
      "title": "Localport",
      "type": "integer"
    },
    "remotePort": {
      "title": "Remoteport",
      "type": "integer"
    },
    "remoteHost": {
      "default": "127.0.0.1",
      "title": "Remotehost",
      "type": "string"
    }
  },
  "required": [
    "target",
    "localHost",
    "localPort",
    "remotePort"
  ],
  "title": "forward_local_to_remoteArguments",
  "type": "object"
}
```
