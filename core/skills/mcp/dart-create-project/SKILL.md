---
name: dart-create-project
description: "Creates a new Dart or Flutter project."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "create_project", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


## Tool Description
Creates a new Dart or Flutter project.

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string",
      "title": "The file URI of the project root to run this tool in.",
      "description": "This must be equal to or a subdirectory of one of the roots allowed by the client. Must be a URI with a `file:` scheme (e.g. file:///absolute/path/to/root)."
    },
    "directory": {
      "type": "string",
      "description": "The subdirectory in which to create the project, must be a relative path."
    },
    "projectType": {
      "type": "string",
      "description": "The type of project: 'dart' or 'flutter'."
    },
    "template": {
      "type": "string",
      "description": "The project template to use (e.g., \"console-full\", \"app\")."
    },
    "platform": {
      "type": "array",
      "description": "The list of platforms this project supports. Only valid for Flutter projects. The allowed values are `web`, `linux`, `macos`, `windows`, `android`, `ios`. Defaults to creating a project for all platforms.",
      "items": {
        "type": "string"
      }
    },
    "empty": {
      "type": "boolean",
      "description": "Whether or not to create an \"empty\" project with minimized boilerplate and example code. Defaults to true."
    }
  },
  "required": [
    "directory",
    "projectType"
  ]
}
```
