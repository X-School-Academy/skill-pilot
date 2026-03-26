---
name: dart-analyze-files
description: "Analyzes the entire project for errors."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "analyze_files", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


## Tool Description
Analyzes the entire project for errors.

## Arguments Schema
```json
{
  "type": "object"
}
```
