# AWS — SSH Port Forwarding from EC2

Forward a port from a remote EC2 instance to localhost via SSH, making a service running on EC2 accessible locally without exposing it to the public internet.

## When to Use

- A service is running on EC2 (web app, API, database proxy, etc.) and you want to access it from a local browser or tool
- Re-establishing a dropped tunnel
- Verifying a service is healthy after deployment

## Preconditions

- Active SSH session or SSH key to the EC2 instance.
  Run `aws-connect-ec2-ssh` action first if no session exists.
- Know the **remote port** the service listens on and the **local port** to bind.

## Skip Condition

Check if the local port is already responding:

```bash
curl -s --max-time 3 http://127.0.0.1:<local-port>/ 2>/dev/null || echo "no response"
```

If it responds, report the tunnel is already active.

## Instructions

### Step 1: Collect parameters

Ask user (or read from previous output) for:

- **EC2 public IP**
- **Remote port** (port the service listens on inside EC2)
- **Local port** (port to bind on localhost; default: same as remote)
- **SSH key path** (default: `.skillpilot/temp/ec2-tmp-ssh`)

### Step 2: Release any existing binding on the local port

```bash
lsof -ti:<local-port> | xargs kill -9 2>/dev/null || true
```

### Step 3: Create SSH tunnel

**Option A — via `terminal-forward-remote-to-local` skill:**

```json
{
  "target": "ssh:ec2-tmp",
  "remotePort": <remote-port>,
  "localPort": <local-port>
}
```

**Option B — background tmux tunnel via `terminal-open-session`:**

```json
{
  "command": "ssh",
  "args": [
    "-N",
    "-L", "<local-port>:127.0.0.1:<remote-port>",
    "-o", "StrictHostKeyChecking=no",
    "-i", "<ssh-key-path>",
    "ubuntu@<public-ip>"
  ],
  "target": "local",
  "lifecycle": "tmux"
}
```

### Step 4: Verify tunnel

Wait 3 seconds, then probe the local port:

```bash
curl -s --max-time 5 http://127.0.0.1:<local-port>/
```

If no response after 10 seconds, check that the service is running on EC2 (connect via SSH and inspect the process or service logs).

### Step 5: Open in browser (if applicable)

Use `agent-browser` skill to open `http://127.0.0.1:<local-port>`.

### Step 6: Report result

```
SSH tunnel:    active (local <local-port> → EC2 <public-ip>:<remote-port>)
Local URL:     http://127.0.0.1:<local-port>
Health check:  OK
```

## Common Issues

- **Port already in use**: `lsof -ti:<local-port> | xargs kill -9`
- **Tunnel exits immediately**: SSH key expired — re-run `aws-connect-ec2-ssh` to push a new key
- **Service not responding**: connect via SSH and check the service is running (e.g. `systemctl status <service>` or `ps aux | grep <process>`)
