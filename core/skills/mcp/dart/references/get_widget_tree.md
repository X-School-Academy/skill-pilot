# get_widget_tree

Retrieves the widget tree from the active Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Usage
```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "get_widget_tree", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "type": "object"
}
```
