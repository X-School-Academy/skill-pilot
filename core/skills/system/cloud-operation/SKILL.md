---
name: cloud-operation
description: Cloud infrastructure operations for AWS and RunPod. Use when managing EC2 instances, configuring AWS credentials, SSH connections, port forwarding, or managing RunPod GPU pods and serverless endpoints. Supports AWS and RunPod; extensible to other providers.
---

# Cloud Operation

Manage cloud infrastructure across supported providers. Select the action and provider below, then follow the linked reference.

## Your Roles in This Skill

- **SysOps Engineer**: Provision and configure cloud compute and networking
- **Security Engineer**: Enforce least-privilege access and secure credential handling

## Role Communication

Announce your active role before taking any action:

```
As a {Role}, I will {action description}
```

## Action Index

### AWS

| Action | Reference | When to use |
|--------|-----------|-------------|
| Set up AWS credentials & MCP | [aws-enable-cli.md](references/aws-enable-cli.md) | No AWS credentials configured yet, or MCP disabled |
| Provision EC2 instance (VPC + networking) | [aws-setup-ec2.md](references/aws-setup-ec2.md) | Launching a new EC2 server |
| Connect to EC2 via SSH | [aws-connect-ec2-ssh.md](references/aws-connect-ec2-ssh.md) | Opening an SSH session to an EC2 instance |
| Forward a remote EC2 port to localhost | [aws-ec2-tunnel.md](references/aws-ec2-tunnel.md) | Accessing a service running on EC2 from a local browser or tool |
| EC2 CLI reference (concepts, commands, troubleshooting) | [aws-ec2-cli.md](references/aws-ec2-cli.md) | Constructing or debugging EC2 API calls |

### RunPod

| Action | Reference | When to use |
|--------|-----------|-------------|
| Manage GPU pods, serverless, templates, volumes | [runpod-manage.md](references/runpod-manage.md) | Any RunPod workload operation |

## Execution Rule

- Never run raw `aws ...` shell commands directly.
- Execute all AWS operations through `aws-api` skill (`call_aws` tool).
- If an AWS command shape, flag, or parameter is unclear, use `aws-api` skill (`suggest_aws_commands` tool) first, then run through `aws-api` (`call_aws`).

## Common Preconditions

- **AWS operations**: AWS credentials in `config/.env` — run the `enable-cli` action if missing.
- **RunPod operations**: `runpodctl` installed and API key configured via `runpodctl doctor`.

## Adding a New Cloud Provider

1. Create `references/<provider>-<action>.md` with the provider's workflow.
2. Add a new section to the Action Index table above.
