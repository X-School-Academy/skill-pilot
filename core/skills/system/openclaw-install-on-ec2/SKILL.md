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
  ```bash
  core/bin/keys-safe-guard get_key_value DISCORD_BOT_TOKEN DISCORD_SERVER_ID DISCORD_USER_ID
  ```
  Run skill `create-discord-bot` if not set.

- **OpenAI Codex account:** Confirm with user that they have a ChatGPT/Codex subscription — required for the OAuth step.

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

### Step 2: Generate gateway token on EC2

```bash
node -e "const c=require('crypto');console.log(c.randomBytes(32).toString('hex'))"
```

Capture the output as `OPENCLAW_GATEWAY_TOKEN`. Show it to the user and ask them to save it
(e.g. in a password manager or a local file of their choice).

### Step 3: Read Discord credentials from local .env

Run locally:
```bash
core/bin/keys-safe-guard get_key_value DISCORD_BOT_TOKEN DISCORD_SERVER_ID DISCORD_USER_ID
```

Use these values to construct the config. Do not log `DISCORD_BOT_TOKEN` in full.

### Step 4: Write openclaw.json on EC2

Use `terminal-send-session-input` to write `~/.openclaw/openclaw.json`.
Pass secret values as shell variables to avoid them appearing in the heredoc literally:

```bash
GATEWAY_TOKEN="<OPENCLAW_GATEWAY_TOKEN>"
DISCORD_TOKEN="<DISCORD_BOT_TOKEN>"
SERVER_ID="<DISCORD_SERVER_ID>"
USER_ID="<DISCORD_USER_ID>"

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
```

## Common Issues

- **`openclaw` not found after install**: add npm global bin to PATH; source ~/.bashrc
- **`openclaw doctor` fails**: check JSON5 syntax in `~/.openclaw/openclaw.json`
- **Codex OAuth URL doesn't open**: ensure the user's local browser has internet access and they are signed into OpenAI
- **Discord pairing code expired**: codes expire in 1 hour — restart pairing if needed
- **systemd service fails to start**: run `journalctl -u openclaw -n 50` and check ExecStart path with `which openclaw`
