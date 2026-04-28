# remove_roots

Removes one or more project roots previously added via the add_roots tool.

## Usage
```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "remove_roots", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "uris": {
      "type": "array",
      "description": "All the project roots to remove from this server.",
      "items": {
        "type": "string",
        "description": "The URIs of the roots to remove."
      }
    }
  }
}
```
