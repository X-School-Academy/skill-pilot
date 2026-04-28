# connect_dart_tooling_daemon

Connects to the Dart Tooling Daemon. You should get the uri either from available tools or the user, do not just make up a random URI to pass. When asking the user for the uri, you should suggest the "Copy DTD Uri to clipboard" action. When reconnecting after losing a connection, always request a new uri first.

## Usage
```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "connect_dart_tooling_daemon", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "uri": {
      "type": "string"
    }
  },
  "required": [
    "uri"
  ]
}
```
