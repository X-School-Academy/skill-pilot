---
name: dart-analyze-files
description: "Analyzes the entire project for errors."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "analyze_files", "arguments": {}}'
```

## Tool Description
Analyzes the entire project for errors.

## Arguments Schema
```json
{
  "type": "object"
}
```
