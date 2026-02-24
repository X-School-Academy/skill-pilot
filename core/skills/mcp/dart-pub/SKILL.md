---
name: dart-pub
description: "Runs a pub command for the given project roots, like `dart pub get` or `flutter pub add`."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "pub", "arguments": {}}'
```

## Tool Description
Runs a pub command for the given project roots, like `dart pub get` or `flutter pub add`.

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "command": {
      "type": "string",
      "title": "The pub command to run.",
      "description": "Currently only `add`, `get`, `remove`, and `upgrade` are supported."
    },
    "packageName": {
      "type": "string",
      "title": "The package name to run the command for.",
      "description": "This is required for the `add`, and `remove` commands."
    },
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
  },
  "required": [
    "command"
  ]
}
```
