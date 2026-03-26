---
name: terminal-scp-upload
description: "Start an asynchronous SFTP upload from localPath to remotePath on an SSH target."
---

Use this tool when you need to transfer a local file to a remote SSH host.
        Best for uploading configuration files, binaries, or other artifacts to remote servers.

        Args:
            target: SSH profile identifying the remote host. Must be "ssh:<profile>" (e.g. "ssh:prod", "ssh:dev").
                    Profiles are defined in the server's SSH config file (config.json).
            localPath: Absolute path to the local file to upload. The file must exist before calling.
                       Example: "/home/user/deploy.tar.gz"
            remotePath: Destination path on the remote host.
                        Example: "/opt/app/deploy.tar.gz"

        Returns:
            JSON object with:
            - accepted: true when the operation has been queued
            - operationId: ID to track progress via get_operation_status
            - status: initial operation status (e.g. "pending")
            - target: the SSH target used

        Do not use this tool:
            - to download files from a remote host; use scp_download instead
            - for local-to-local file operations; use exec_command with cp instead
            - with target="local"; this tool only supports SSH targets

        Notes:
            - The upload runs asynchronously. Poll get_operation_status with the operationId for completion.
            - The local file must exist before calling this tool.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "scp_upload", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


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
