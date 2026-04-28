# get_active_location

Retrieves the current active location (e.g., cursor position) in the connected editor. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Usage
```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "get_active_location", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "type": "object"
}
```
