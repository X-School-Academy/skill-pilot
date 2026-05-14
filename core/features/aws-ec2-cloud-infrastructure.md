# Feature Retrieval Index: AWS and EC2 Cloud Infrastructure

## Retrieval Keywords

AWS, EC2, cloud infrastructure, AWS CLI, enable-aws-cli, setup-aws-ec2, openclaw, openclaw-install-on-ec2, openclaw-connect-tunnel, connect-ec2-ssh, SSH tunnel, cloud setup, remote server, EC2 instance, aws-api-call-aws

## Scope

- AWS CLI setup and configuration skill
- EC2 instance provisioning and SSH connection
- OpenClaw tunnel setup for remote access
- Excludes: general SSH terminal (see `mcp-terminal-server.md`), Docker (see extensions/docker)

## Main Behavior

- `enable-aws-cli` skill configures AWS CLI credentials and profiles
- `setup-aws-ec2` skill provisions and configures an EC2 instance
- `connect-ec2-ssh` skill establishes SSH connection to an EC2 instance
- `openclaw-install-on-ec2` installs OpenClaw on an EC2 instance
- `openclaw-connect-tunnel` creates a secure tunnel to an EC2 instance
- AWS operations use the `aws-api-call-aws` skill (not direct CLI)
- Workflows: `setup-openclaw.json`, `setup-openclaw-2.json`

## Code Map

- `core/skills/system/enable-aws-cli/` — AWS CLI setup skill
- `core/skills/system/setup-aws-ec2/` — EC2 setup skill
- `core/skills/system/connect-ec2-ssh/` — EC2 SSH connection skill
- `core/skills/system/openclaw-install-on-ec2/` — OpenClaw EC2 installer skill
- `core/skills/system/openclaw-connect-tunnel/` — OpenClaw tunnel skill
- `core/workflows/setup-openclaw.json` — OpenClaw setup workflow
- `core/workflows/setup-openclaw-2.json` — OpenClaw setup workflow v2

## Search Commands

```bash
find core/skills/system/enable-aws-cli/ -type f
find core/skills/system/setup-aws-ec2/ -type f
find core/skills/system/connect-ec2-ssh/ -type f
cat core/workflows/setup-openclaw.json | head -20
```

## Related Features

- `core/features/mcp-terminal-server.md`
- `core/features/skill-agent-system.md`

## Update Notes

- AWS credentials stored in `config/.env`; protected by keys-safe-guard
- Memory note: always use `aws-api-call-aws` skill for AWS CLI operations, not direct Bash aws commands
