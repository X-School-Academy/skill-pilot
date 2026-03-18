---
name: openclaw-install-on-ec2
description: Install OpenClaw on an AWS EC2 instance via SSH session. Runs the official installer, writes openclaw.json with gateway config and Discord channel, authenticates OpenAI Codex via OAuth, sets up systemd service, and pairs the Discord bot.
---

# OpenClaw Setup — Install OpenClaw on EC2

Install and fully configure OpenClaw on the EC2 instance:
1. Install via official installer script
2. Write `openclaw.json` with gateway config, Discord channel, and Codex model
3. Authenticate with OpenAI Codex via OAuth (user opens browser locally)
4. Install and start the systemd service
5. Pair the Discord bot

## When to Use This Skill

- OpenClaw is not yet installed on the EC2 instance
- Reconfiguring OpenClaw after a fresh instance or token reset
- Setting up OpenAI Codex OAuth and Discord bot pairing for the first time

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Install OpenClaw, write config, run auth flows
- **SysOps Engineer**: Set up systemd service for persistence
- **Security Engineer**: Generate gateway token, load Discord token from .env — never echo secrets in full

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Preconditions

- Active SSH session to the EC2 instance (have a session ID ready)
  Run skill `connect-ec2-ssh` if no session is active.

- Discord bot token configured in `config/.env`:
  Use skill `key-safe` to get `OPENCLAW_DISCORD_BOT_TOKEN`, `OPENCLAW_DISCORD_SERVER_ID` (Optional), and `OPENCLAW_DISCORD_USER_ID` (Optional).
  Run skill `create-discord-bot` if not set.

- **OpenAI Codex account:** Confirm with user that they have a ChatGPT/Codex subscription — required for the OAuth step.

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (OpenClaw version, service health, OAuth status, Discord pairing status, and gateway access details) so downstream agents can safely continue.

## Skip Condition

Check via SSH session whether OpenClaw is already installed and running:

```bash
# via terminal-send-session-input on <session_id>
openclaw status
```

If the gateway responds, ask user whether to skip or reinstall.

## Instructions

All remote commands are run via `terminal-send-session-input` on the active SSH session ID.

### Step 1: Install OpenClaw (no onboarding)

```bash
curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash -s -- --no-onboard
```

Fix PATH if `openclaw` is not found after install:
```bash
export PATH="$(npm prefix -g)/bin:$PATH"
echo 'export PATH="$(npm prefix -g)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify:
```bash
openclaw --version
mkdir -p ~/.openclaw/workspace
```

Capture the version string.

### Step 2: Generate gateway token on EC2 and store it with key-safe

```bash
node -e "const c=require('crypto');console.log(c.randomBytes(32).toString('hex'))"
```

Capture the output as `OPENCLAW_GATEWAY_TOKEN`.

Immediately save it locally with skill `key-safe` using `put_key_values`:

```bash
core/bin/keys-safe-guard --gui put_key_values OPENCLAW_GATEWAY_TOKEN=<generated-token>
```

Do not write the token into docs, chat summaries, local notes, or task files.
When the value is needed later, retrieve it through skill `key-safe` or by running:

```bash
core/bin/keys-safe-guard --gui get_key_value OPENCLAW_GATEWAY_TOKEN
```

### Step 3: Read Discord credentials from local .env

Run locally:
Use skill `key-safe` to get:
- `OPENCLAW_GATEWAY_TOKEN`
- `OPENCLAW_DISCORD_BOT_TOKEN`
- `OPENCLAW_DISCORD_SERVER_ID`
- `OPENCLAW_DISCORD_USER_ID`

Use these values to construct the config. Do not log secret values in full.

### Step 4: Write openclaw.json on EC2

Use `terminal-send-session-input` to write `~/.openclaw/openclaw.json`.
Pass secret values as shell variables to avoid them appearing in the heredoc literally:

```bash
GATEWAY_TOKEN="<retrieve with key-safe>"
DISCORD_TOKEN="<retrieve with key-safe>"
SERVER_ID="<retrieve with key-safe>"
USER_ID="<retrieve with key-safe>"

mkdir -p ~/.openclaw
cat > ~/.openclaw/openclaw.json << ENDCONFIG
{
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace",
      model: { primary: "openai-codex/gpt-5.3-codex" },
    },
  },
  gateway: {
    mode: "local",
    port: 18789,
    bind: "loopback",
    auth: {
      mode: "token",
      token: "${GATEWAY_TOKEN}",
    },
    controlUi: { enabled: true },
  },
  channels: {
    discord: {
      enabled: true,
      token: "${DISCORD_TOKEN}",
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      guilds: {
        "${SERVER_ID}": {
          requireMention: false,
          users: ["${USER_ID}"],
        },
      },
    },
  },
}
ENDCONFIG
```

Validate:
```bash
openclaw doctor
```

### Step 5: OpenAI Codex OAuth (requires local browser)

> **Note:** EC2 is headless — the authorization URL must be opened in the user's local browser.

```bash
openclaw models auth login --provider openai-codex
```

Copy the authorization URL from the output and show it to the user.

**If the url text is too long and wrapped, you can use tmux command directly to the the url without resize the view**

Ask user to:
1. Open the URL in their local browser
2. Sign in with their OpenAI account (Codex subscription required)
3. Click **Authorize**

The CLI polls and confirms automatically. Wait for:
```
✓ Authenticated with openai-codex
```

Verify:
```bash
openclaw models status
```

### Step 6: Install systemd service

```bash
OPENCLAW_BIN=$(which openclaw)

sudo tee /etc/systemd/system/openclaw.service > /dev/null << EOF
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=${OPENCLAW_BIN} gateway
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable openclaw
sudo systemctl start openclaw
```

Verify:
```bash
sudo systemctl status openclaw
openclaw status
openclaw health
```

### Step 7: Discord bot pairing

1. Ask user to DM the OpenClaw bot in Discord with any message
2. The bot responds with a pairing code
3. Run on EC2:

```bash
openclaw pairing list discord
openclaw pairing approve discord <CODE>
```

Test by sending a message in a Discord server channel — the bot should respond.

### Step 8: Report result

Output result as plain text. If the user asked to save it to a file, write it there.

## Output

Plain text result shown to user:

```
OpenClaw version:    <version>
EC2 instance:        <public-ip>
Gateway:             running on ws://127.0.0.1:18789 (loopback, token auth)
Gateway token:       <show full token — user must save it>
Systemd service:     active (enabled, auto-restart on failure)
OpenAI Codex:        authenticated via OAuth
Discord bot:         paired and responding
WebUI URL:           admin webui url with auth token
```

## Common Issues

- **`openclaw` not found after install**: add npm global bin to PATH; source ~/.bashrc
- **`openclaw doctor` fails**: check JSON5 syntax in `~/.openclaw/openclaw.json`
- **Codex OAuth URL doesn't open**: ensure the user's local browser has internet access and they are signed into OpenAI
- **Discord pairing code expired**: codes expire in 1 hour — restart pairing if needed
- **systemd service fails to start**: run `journalctl -u openclaw -n 50` and check ExecStart path with `which openclaw`
- **OpenClaw crashes with Node.js OOM (`Ineffective mark-compacts near heap limit`)**:
  On small ARM instances such as `t4g.small` (2 GiB RAM), OpenClaw CLI startup can exceed Node's default heap budget. Swap alone may prevent kernel OOM kills, but it does not reliably raise V8's heap ceiling enough for OpenClaw startup.

  Diagnose first:
  ```bash
  free -h
  sudo swapon --show
  openclaw doctor
  ```

  Temporary workaround for the current shell:
  ```bash
  export NODE_OPTIONS="--max-old-space-size=4096"
  openclaw doctor
  ```

  If that resolves the crash, persist it for both interactive use and systemd:
  ```bash
  echo 'export NODE_OPTIONS="--max-old-space-size=4096"' >> ~/.bashrc
  source ~/.bashrc
  ```

  Add the same setting to the service unit:
  ```bash
  OPENCLAW_BIN=$(which openclaw)
  sudo tee /etc/systemd/system/openclaw.service > /dev/null << EOF
  [Unit]
  Description=OpenClaw Gateway
  After=network-online.target
  Wants=network-online.target

  [Service]
  Type=simple
  User=ubuntu
  WorkingDirectory=/home/ubuntu
  Environment=NODE_OPTIONS=--max-old-space-size=4096
  ExecStart=${OPENCLAW_BIN} gateway
  Restart=on-failure
  RestartSec=5
  StandardOutput=journal
  StandardError=journal

  [Install]
  WantedBy=multi-user.target
  EOF

  sudo systemctl daemon-reload
  sudo systemctl restart openclaw
  ```

  If the crash still occurs, create swap at `2G` first. If `2G` is already present or still insufficient, increase it in `1G` steps (`3G`, `4G`, `5G`, and so on, and increase `--max-old-space-size` as needed) and retry after each change:
  ```bash
  ls -lh /swapfile
  sudo swapon -s

  sudo swapoff /swapfile
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  sudo swapon --show
  ```

  Safe resize flow:
  1. Check whether `/swapfile` exists with `ls -lh /swapfile`.
  2. If swap is active, verify it with `sudo swapon -s`.
  3. Start with `2G`. If OpenClaw still crashes, turn swap off and recreate `/swapfile` at `3G`, then `4G`, then `5G`, increasing by `1G` each retry.
  4. Ensure `/etc/fstab` contains the persistent entry. If it does not exist yet, add:
  ```bash
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```

  Example resize from `2G` to `3G`:
  ```bash
  sudo swapoff /swapfile
  sudo fallocate -l 3G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  sudo swapon --show
  ```
