# scp_download

Start an asynchronous SFTP download from an SSH target to localPath.

        Use this tool when you need to retrieve a file from a remote SSH host to the local machine.
        Best for fetching logs, outputs, or artifacts generated on a remote server.

        Args:
            target: SSH profile identifying the remote host. Must be "ssh:<profile>" (e.g. "ssh:prod", "ssh:dev").
                    Profiles are defined in the server's SSH config file (config.json).
            remotePath: Path to the file on the remote host.
                        Example: "/var/log/app.log", "/opt/app/output.tar.gz"
            localPath: Destination path on the local machine. Parent directories are created if needed.
                       Example: "/tmp/app.log", "/home/user/downloads/output.tar.gz"

        Returns:
            JSON object with:
            - accepted: true when the operation has been queued
            - operationId: ID to track progress via get_operation_status
            - status: initial operation status (e.g. "pending")
            - target: the SSH target used

        Do not use this tool:
            - to upload files to a remote host; use scp_upload instead
            - with target="local"; this tool only supports SSH targets

        Notes:
            - The download runs asynchronously. Poll get_operation_status with the operationId for completion.
            - Local parent directories are created automatically if they do not exist.

## Usage
```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "scp_download", "arguments": {}}'
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
    "remotePath": {
      "title": "Remotepath",
      "type": "string"
    },
    "localPath": {
      "title": "Localpath",
      "type": "string"
    }
  },
  "required": [
    "target",
    "remotePath",
    "localPath"
  ],
  "title": "scp_downloadArguments",
  "type": "object"
}
```
