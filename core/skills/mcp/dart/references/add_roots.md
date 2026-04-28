# add_roots

Adds one or more project roots. Tools are only allowed to run under these roots, so you must call this function before passing any roots to any other tools.

## Usage
```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "add_roots", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "roots": {
      "type": "array",
      "description": "All the project roots to add to this server.",
      "items": {
        "type": "object",
        "properties": {
          "uri": {
            "type": "string",
            "description": "The URI of the root."
          },
          "name": {
            "type": "string",
            "description": "An optional name of the root."
          }
        },
        "required": [
          "uri"
        ]
      }
    }
  }
}
```
