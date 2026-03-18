---
name: aws-api-call-aws
description: "Execute AWS CLI commands with validation and proper error handling. This is the PRIMARY tool to use when you are confident about the exact AWS CLI command needed to fulfill a user's request. Always prefer this tool over…"
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "aws-api", "tool_name": "call_aws", "arguments": {}}'
```

## Tool Description
Execute AWS CLI commands with validation and proper error handling. This is the PRIMARY tool to use when you are confident about the exact AWS CLI command needed to fulfill a user's request. Always prefer this tool over 'suggest_aws_commands' when you have a specific command in mind.
    Key points:
    - The command MUST start with "aws" and follow AWS CLI syntax
    - Commands are executed in ap-southeast-2 region by default
    - For cross-region or account-wide operations, explicitly include --region parameter
    - All commands are validated before execution to prevent errors
    - Supports pagination control via max_results parameter
    - Commands can only reference files within the working directory (/var/folders/_0/ff3ds_c93pv14wnhx96y00400000gn/T/aws-api-mcp/workdir); use forward slashes (/) regardless of the system (e.g. if working directory is 'c:/tmp/workdir', use 'c:/tmp/workdir/subdir/file.txt' or 'subdir/file.txt'); relative paths resolve from the working directory.
    - You can use `--region *` to run a command on all regions enabled in the account.
    - Do not generate explicit batch calls for iterating over all regions, use `--region *` instead.

    Single Command Mode:
    - You can run a single AWS CLI command using this tool.
    - Example:
        call_aws(cli_command="aws s3api list-buckets --region us-east-1")

    Batch Running:
    - The tool can also run multiple independent commands at the same time.
    - Call this tool with multiple CLI commands whenever possible.
    - Batch calling is especially useful where you need to run a command multiple times with different parameter values
    - Example:
        call_aws(
            cli_command=[
                "aws s3api get-bucket-website --bucket bucket1",
                "aws s3api get-bucket-website --bucket bucket2"
            ]
        )
    - You can call at most 20 CLI commands in batch mode.

    Best practices for command generation:
    - Always use the most specific service and operation names
    - Always use the working directory when writing files, unless user explicitly mentioned another directory
    - Include --region when operating across regions
    - Only use filters (--filters, --query, --prefix, --pattern, etc) when necessary or user explicitly asked for it
    - Always use the tool in batch mode whenever it's possible.

    Command restrictions:
    - DO NOT use bash/zsh pipes (|) or any shell operators
    - DO NOT use bash/zsh tools like grep, awk, sed, etc.
    - DO NOT use shell redirection operators (>, >>, <)
    - DO NOT use command substitution ($())
    - DO NOT use shell variables or environment variables

    Common pitfalls to avoid:
    1. Missing required parameters - always include all required parameters
    2. Incorrect parameter values - ensure values match expected format
    3. Missing --region when operating across regions

    Returns:
        CLI execution results with API response data or error message

## Arguments Schema
```json
{
  "additionalProperties": false,
  "properties": {
    "cli_command": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        }
      ],
      "description": "A single command or a list of complete AWS CLI commands to execute"
    },
    "max_results": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Optional limit for number of results (useful for pagination)"
    }
  },
  "required": [
    "cli_command"
  ],
  "type": "object"
}
```
