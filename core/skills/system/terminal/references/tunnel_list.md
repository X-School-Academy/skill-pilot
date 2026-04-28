# tunnel_list

List all active SSH tunnels managed by this server.

        Use this tool when you need to see which port-forward tunnels are currently open.
        Best for auditing active connections or finding a tunnelId before calling tunnel_stop.

        Returns:
            JSON object with:
            - tunnels: list of active tunnel objects, each containing tunnelId, direction, localAddress, and remoteAddress.

        Do not use this tool:
            - to stop a tunnel; use tunnel_stop instead

## Usage
```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "tunnel_list", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "properties": {},
  "title": "tunnel_listArguments",
  "type": "object"
}
```
