---
name: terminal-scp-upload
description: "Start an asynchronous SFTP upload from localPath to remotePath on an SSH target."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "scp_upload", "arguments": {}}'
```

## Tool Description
Start an asynchronous SFTP upload from localPath to remotePath on an SSH target.

## Arguments Schema
```json
{
  "properties": {
    "target": {
      "title": "Target",
      "type": "string"
    },
    "localPath": {
      "title": "Localpath",
      "type": "string"
    },
    "remotePath": {
      "title": "Remotepath",
      "type": "string"
    }
  },
  "required": [
    "target",
    "localPath",
    "remotePath"
  ],
  "title": "scp_uploadArguments",
  "type": "object"
}
```
