# Feature Retrieval Index: AWS and EC2 Cloud Infrastructure

## Retrieval Keywords

AWS, EC2, cloud infrastructure, AWS CLI, cloud-operation, enable-aws-cli, setup-aws-ec2, connect-ec2-ssh, SSH tunnel, cloud setup, remote server, EC2 instance, aws-api-call-aws, RunPod, runpodctl, GPU pod, serverless endpoint

## Scope

- AWS credential setup and MCP activation
- EC2 instance provisioning, SSH connection, and port forwarding
- RunPod GPU pod and serverless endpoint management
- EC2 CLI reference (concepts, commands, troubleshooting)
- Excludes: general SSH terminal (see `mcp-terminal-server.md`), Docker (see extensions/docker)

## Main Behavior

- `cloud-operation` skill is the single entry point for all AWS and RunPod cloud tasks
- Actions are routed via the skill's index table to the appropriate reference file
- AWS operations use `aws-api-call-aws` skill (never direct `aws` CLI commands)
- RunPod operations use the `runpodctl` CLI

## Code Map

- `core/skills/system/cloud-operation/` — unified cloud operations skill
  - `SKILL.md` — action index and routing table
  - `references/aws-enable-cli.md` — AWS credential setup and MCP activation
  - `references/aws-setup-ec2.md` — EC2 instance provisioning (VPC, subnet, security group)
  - `references/aws-connect-ec2-ssh.md` — SSH connection via EC2 Instance Connect
  - `references/aws-ec2-tunnel.md` — SSH port forwarding from EC2 to localhost
  - `references/aws-ec2-cli.md` — EC2 CLI reference, concepts, and troubleshooting
  - `references/runpod-manage.md` — RunPod pods, serverless, templates, volumes

## Search Commands

```bash
find core/skills/system/cloud-operation/ -type f
cat core/skills/system/cloud-operation/SKILL.md
```

## Related Features

- `core/features/mcp-terminal-server.md`
- `core/features/skill-agent-system.md`

## Update Notes

- AWS credentials stored in `config/.env`; protected by keys-safe-guard
- Always use `aws-api-call-aws` skill for AWS CLI operations, not direct Bash aws commands
