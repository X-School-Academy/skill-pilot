---
name: aws-api
description: "Execute and suggest AWS CLI commands with validation, batch execution, and multi-region support."
---

## Tools

Select the tool that matches the task. Read its reference file only when you are ready to invoke it.

- **call_aws** — Execute AWS CLI commands with validation and proper error handling. This is the PRIMARY tool to use when you are confident about the exact AWS CLI command needed to fulfill a user's request. Always prefer this tool over 'suggest_aws_commands' when you have a specific command in mind. ([details](references/call_aws.md))
- **suggest_aws_commands** — Suggest AWS CLI commands based on a natural language query. This is a FALLBACK tool to use when you are uncertain about the exact AWS CLI command needed to fulfill a user's request. ([details](references/suggest_aws_commands.md))
