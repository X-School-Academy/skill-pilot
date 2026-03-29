---
name: dart-dart-fix
description: "Runs `dart fix --apply` for the given project roots."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "dart_fix", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


## Tool Description
Runs `dart fix --apply` for the given project roots.

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "roots": {
      "type": "array",
      "title": "All projects roots to run this tool in.",
      "items": {
        "type": "object",
        "properties": {
          "root": {
            "type": "string",
            "title": "The file URI of the project root to run this tool in.",
            "description": "This must be equal to or a subdirectory of one of the roots allowed by the client. Must be a URI with a `file:` scheme (e.g. file:///absolute/path/to/root)."
          }
        },
        "required": [
          "root"
        ]
      }
    }
  }
}
```
