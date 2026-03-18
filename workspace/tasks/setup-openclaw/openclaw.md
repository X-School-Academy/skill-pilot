# OpenClaw Configuration — app-server

## Installation Summary

| Field               | Value                                      |
|---------------------|--------------------------------------------|
| OpenClaw version    | 2026.3.13 (61d171a)                        |
| EC2 instance        | i-0c91d6d3ea988927f (54.79.12.72)          |
| Region              | ap-southeast-2                             |
| Install path        | /home/ubuntu/.npm-global/bin/openclaw      |
| Config file         | ~/.openclaw/openclaw.json                  |
| Workspace           | ~/.openclaw/workspace                      |

## Gateway

| Field           | Value                                      |
|-----------------|--------------------------------------------|
| Mode            | local (loopback only)                      |
| Address         | ws://127.0.0.1:18789                       |
| Auth mode       | token                                      |
| Gateway token   | Stored in key-safe as `OPENCLAW_GATEWAY_TOKEN` |
| Control UI      | enabled                                    |

Retrieve the token only when needed:

```bash
core/bin/keys-safe-guard --gui get_key_value OPENCLAW_GATEWAY_TOKEN
```

Agents should retrieve this value through skill `key-safe` instead of reading or documenting the secret directly.

## Systemd Service

| Field       | Value                                      |
|-------------|--------------------------------------------|
| Service     | openclaw.service                           |
| Status      | active (enabled, auto-restart on failure)  |
| Managed by  | systemd                                    |

```bash
sudo systemctl status openclaw
sudo systemctl restart openclaw
journalctl -u openclaw -n 50
```

## Discord Channel

| Field           | Value                                      |
|-----------------|--------------------------------------------|
| Status          | ON / OK                                    |
| Bot user ID     | 1480121635800481975                        |
| DM policy       | pairing                                    |
| Group policy    | allowlist                                  |

## OpenAI Codex

| Field   | Value                              |
|---------|------------------------------------|
| Status  | **Not authenticated** (skipped)    |
| Action  | Run `openclaw models auth login --provider openai-codex` to authenticate later |

## Swap & Memory

| Field      | Value                          |
|------------|--------------------------------|
| Swap       | 2G /swapfile (active, in fstab) |
| NODE_OPTIONS | `--max-old-space-size=4096` (in ~/.bashrc and systemd unit) |

## Remote Access

To access the gateway from your local machine, use the `openclaw-connect-tunnel` skill to forward port 18789.

```bash
# After tunnel is established:
export OPENCLAW_GATEWAY_URL=ws://localhost:18789
export OPENCLAW_GATEWAY_TOKEN="$(core/bin/keys-safe-guard --gui get_key_value OPENCLAW_GATEWAY_TOKEN)"
```
