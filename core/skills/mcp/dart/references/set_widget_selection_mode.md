# set_widget_selection_mode

Enables or disables widget selection mode in the active Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Usage
```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "set_widget_selection_mode", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "enabled": {
      "type": "boolean",
      "title": "Enable widget selection mode"
    }
  },
  "required": [
    "enabled"
  ]
}
```
