---
name: connect-ec2-ssh
description: Generate a temp SSH key, push it to an EC2 instance via EC2 Instance Connect, update config/ssh.json5, and open a persistent tmux SSH session. Returns session ID and connection info. Reusable for any EC2 SSH connection task.
---

# Connect to EC2 via Temp SSH

Generate a temporary ed25519 SSH key, push it to an EC2 instance via EC2 Instance Connect
(no permanent key pair needed), update the local SSH profile, and open a persistent tmux session.

## When to Use This Skill

- Connecting to any EC2 instance without a pre-existing key pair
- SSH key has expired or a previous session was lost
- Opening a fresh SSH session to any EC2 Ubuntu instance

## Your Roles in This Skill

- **SysOps Engineer**: Generate key, push via Instance Connect, open tmux session
- **Security Engineer**: Use short-lived key only — no permanent key pair stored on AWS

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Preconditions

- AWS credentials configured — run skill `enable-aws-cli` if needed
- EC2 instance is running — have instance ID, public IP, and region ready
  (from skill `setup-aws-ec2` output or provided by user)

Verify AWS credentials:
```bash
core/bin/keys-safe-guard get_key_value AWS_ACCESS_KEY_ID AWS_REGION
```

## Skip Condition

Ask user if an SSH session is already active. If yes, get the session ID and verify with
`terminal-list-sessions` or `terminal-list-tmux-sessions`. If alive, report it and exit.

## Instructions

### Step 1: Collect connection parameters

Ask user (or read from previous skill output) for:
- **Instance ID** (e.g. `i-xxxxxxxxxxxx`)
- **Public IP** (e.g. `x.x.x.x`)
- **Region** (default: read from `.env`)
- **OS user** (default: `ubuntu`)
- **SSH profile name** (default: `ec2-tmp`)

Read region if not provided:
```bash
core/bin/keys-safe-guard get_key_value AWS_REGION
```

### Step 2: Generate temporary SSH key

```bash
mkdir -p .skillpilot/temp
KEY_PATH=".skillpilot/temp/<profile-name>-ssh"
rm -f "${KEY_PATH}" "${KEY_PATH}.pub"
ssh-keygen -t ed25519 -f "${KEY_PATH}" -N "" -C "<profile-name>-tmp"
chmod 600 "${KEY_PATH}"
```

### Step 3: Push public key via EC2 Instance Connect

Use `aws-ec2` skill:

```
aws ec2-instance-connect send-ssh-public-key \
  --instance-id <instance-id> \
  --instance-os-user <os-user> \
  --ssh-public-key file://<KEY_PATH>.pub \
  --region <region>
```

> **Important:** Proceed immediately to Step 4 — the pushed key expires in 60 seconds.

### Step 4: Update config/ssh.json5

Read current `config/ssh.json5` (create with empty `{"profiles":{}}` if missing).
Add or update the named profile:

```json5
{
  "profiles": {
    "<profile-name>": {
      "host": "<public-ip>",
      "port": 22,
      "user": "<os-user>",
      "key": "<KEY_PATH>",
      "timeoutMs": 60000
    }
  }
}
```

Merge with existing profiles — do not overwrite them.

### Step 5: Open SSH session via terminal-open-session skill

```json
{
  "command": "ssh",
  "args": ["-o", "StrictHostKeyChecking=no", "-i", "<KEY_PATH>", "<os-user>@<public-ip>"],
  "target": "local",
  "lifecycle": "tmux",
  "transport": "pty"
}
```

Wait for shell prompt. Save the returned `sessionId`.

### Step 6: Verify connection

Send a quick check via `terminal-send-session-input`:

```bash
echo "connected: $(hostname) $(date)"
```

Confirm output contains EC2 hostname.

### Step 7: Report result

Output result as plain text. If the user asked to save it to a file, write it there.

## Output

Plain text result shown to user:

```
SSH key:          .skillpilot/temp/<profile-name>-ssh (temp, not committed)
EC2 connection:   <os-user>@<public-ip>
Session ID:       <session-id>
Lifecycle:        tmux (survives disconnection)
SSH profile:      <profile-name> added to config/ssh.json5
```

## Common Issues

- **"Connection refused"**: wait 5–10 seconds for sshd to pick up the pushed key
- **"Permission denied (publickey)"**: key expired — re-run Steps 3–5 within 60 seconds of push
- **Instance Connect unavailable**: verify the instance has the endpoint enabled and allows outbound HTTPS
- **ssh.json5 parse error**: validate JSON5 syntax after merging profiles
