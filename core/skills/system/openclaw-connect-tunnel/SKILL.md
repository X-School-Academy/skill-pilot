---
name: openclaw-connect-tunnel
description: Create an SSH tunnel from local port 18789 to the EC2 OpenClaw gateway, then open the WebUI in the local browser. Shows the access URL and prompts for the gateway token. Skip if tunnel is already active.
---

# OpenClaw — Connect via SSH Tunnel

Forward the OpenClaw gateway WebSocket port (18789) from the EC2 instance to localhost via SSH,
then open the Control UI in the local browser.

## When to Use This Skill

- OpenClaw is running on EC2 and the user wants to access the WebUI
- Re-establishing a dropped tunnel
- Verifying OpenClaw health after installation

## Your Roles in This Skill

- **SysOps Engineer**: Create SSH port-forward tunnel and verify connectivity
- **QA Engineer**: Confirm WebUI loads and gateway is healthy

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Preconditions

- AWS credentials configured — run skill `enable-aws-cli` if needed
- OpenClaw installed and running on EC2 — run skill `openclaw-install-on-ec2` if needed
- Have the EC2 public IP and gateway token ready (from the install step output)

Verify AWS credentials:
- Use skill `key-safe` to confirm `AWS_ACCESS_KEY_ID` is available.

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (tunnel status, local URL, health result, and required token/access notes) so downstream agents can safely continue.

## Skip Condition

Check if a tunnel is already active:

```bash
curl -s --max-time 3 http://127.0.0.1:18789/health 2>/dev/null || echo "no response"
```

If the gateway responds, report the tunnel is already active and show the access URL.

## Instructions

### Step 1: Check for active tunnel

```bash
curl -s --max-time 3 http://127.0.0.1:18789/health
```

If response is valid JSON, tunnel is alive — skip to Step 5 (open browser).

### Step 2: Collect connection parameters

Ask user (or read from previous skill output) for:
- **EC2 public IP**
- **Gateway token** (shown in `openclaw-install-on-ec2` output)
- **SSH key path** (default: `.skillpilot/temp/ec2-tmp-ssh` or the path used during connect-ec2-ssh)

If the SSH key is missing, run skill `connect-ec2-ssh` first to generate and push a new key.

### Step 3: Release any existing binding on port 18789

```bash
lsof -ti:18789 | xargs kill -9 2>/dev/null || true
```

### Step 4: Create SSH tunnel using terminal-forward-remote-to-local skill

Use agent skill `terminal-forward-remote-to-local`:

```json
{
  "target": "ssh:ec2-tmp",
  "remotePort": 18789,
  "localPort": 18789
}
```

Or open a background tmux tunnel via `terminal-open-session`:

```json
{
  "command": "ssh",
  "args": [
    "-N",
    "-L", "18789:127.0.0.1:18789",
    "-o", "StrictHostKeyChecking=no",
    "-i", "<ssh-key-path>",
    "ubuntu@<public-ip>"
  ],
  "target": "local",
  "lifecycle": "tmux"
}
```

Wait 3 seconds for the tunnel to establish, then probe:

```bash
curl -s --max-time 5 http://127.0.0.1:18789/health
```

If no response after 10 seconds, check that the OpenClaw service is running on EC2 (connect via SSH and run `openclaw status`).

### Step 5: Open WebUI in local browser

```bash
playwright-cli open "http://127.0.0.1:18789" --extension --headed
```

If a token prompt appears, enter the gateway token.

Confirm the OpenClaw Control UI loads.

### Step 6: Report result

Output result as plain text. If the user asked to save it to a file, write it there.

## Output

Plain text result shown to user:

```
SSH tunnel:       active (local 18789 → EC2 <public-ip>:18789)
OpenClaw WebUI:   http://127.0.0.1:18789
Gateway token:    <show token if user needs it>
Health check:     OK

=== OpenClaw EC2 Setup Complete ===

EC2 public IP:    <public-ip>
OpenClaw:         running (systemd, auto-restart enabled)
Provider:         openai-codex (OAuth)
Discord:          connected (bot paired, guild allowlist active)
WebUI:            http://127.0.0.1:18789 (SSH tunnel)

Next steps:
  Leave running   — ~$15/month, always-on
  Stop instance   — aws ec2 stop-instances --instance-ids <id>
  Terminate       — aws ec2 terminate-instances --instance-ids <id>
```

## Common Issues

- **Port 18789 in use**: `lsof -ti:18789 | xargs kill -9`
- **Tunnel exits immediately**: SSH key expired — re-run `connect-ec2-ssh` to push a new key
- **WebUI shows "connection refused"**: OpenClaw service may be down — connect via SSH and run `sudo systemctl restart openclaw`
- **Token rejected**: verify the gateway token matches the one generated during install
