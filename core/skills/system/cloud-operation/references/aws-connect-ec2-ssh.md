# AWS — Connect to EC2 via SSH

Generate a temporary ed25519 SSH key, push it to an EC2 instance via EC2 Instance Connect (no permanent key pair needed), update the local SSH profile, and open a persistent tmux session.

## When to Use

- Connecting to any EC2 instance without a pre-existing key pair
- SSH key has expired or a previous session was lost
- Opening a fresh SSH session to any EC2 Ubuntu instance

## Preconditions

- AWS credentials configured — run `aws-enable-cli` action if needed.
- EC2 instance is running — have instance ID, public IP, and region ready (from `aws-setup-ec2` output or provided by user).
- Verify: use skill `key-safe-sudo` to confirm `AWS_ACCESS_KEY_ID` and `AWS_REGION`.

## Execution Rule

All AWS CLI commands are reference only. Execute through `aws-api` (`call_aws`). For unclear commands, use `aws-api` skill (`suggest_aws_commands` tool) first.

## Skip Condition

Ask user if an SSH session is already active. If yes, verify with `terminal-list-sessions` or `terminal-list-tmux-sessions`. If alive, report it and exit.

## Instructions

### Step 1: Collect connection parameters

Ask user (or read from previous output) for:

- **Instance ID** (e.g. `i-xxxxxxxxxxxx`)
- **Public IP** (e.g. `x.x.x.x`)
- **Region** (default: read from `.env` via `key-safe-sudo`)
- **OS user** (default: `ubuntu`)
- **SSH profile name** (default: `ec2-tmp`)

### Step 2: Generate temporary SSH key

```bash
mkdir -p .skillpilot/temp
KEY_PATH=".skillpilot/temp/<profile-name>-ssh"
rm -f "${KEY_PATH}" "${KEY_PATH}.pub"
ssh-keygen -t ed25519 -f "${KEY_PATH}" -N "" -C "<profile-name>-tmp"
chmod 600 "${KEY_PATH}"
```

### Step 3: Push public key via EC2 Instance Connect

Reference (execute via `aws-api` (`call_aws`)):

```
aws ec2-instance-connect send-ssh-public-key \
  --instance-id <instance-id> \
  --instance-os-user <os-user> \
  --ssh-public-key file://<KEY_PATH>.pub \
  --region <region>
```

> **Important:** Proceed immediately to Step 4 — the pushed key expires in 60 seconds.

### Step 4: Update config/ssh.json5

Read current `config/ssh.json5` (create with `{"profiles":{}}` if missing). Add or update the named profile:

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

### Step 5: Open SSH session

Use `terminal-open-session` skill:

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

Send via `terminal-send-session-input`:

```bash
echo "connected: $(hostname) $(date)"
```

Confirm output contains EC2 hostname.

### Step 7: Report result

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
