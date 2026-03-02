# Setup OpenClaw on AWS EC2 — Requirement

Set up an OpenClaw gateway instance on AWS EC2 (Ubuntu), authenticate with OpenAI Codex via OAuth,
and connect a Discord bot. The AI follows these steps automatically and only asks the user when human
action is required (browser auth, credential input, account creation).

---

## Step 1 — Playwright Cli readiness check

Verify `playwright-cli` is working before any browser automation.

```bash
playwright-cli open https://www.google.com --extension --headed
```

**If Chrome is not installed:**

```bash
playwright install chrome
```

**If `playwright-cli` is not installed:**

```bash
pnpm install -g @playwright/cli@latest
```

**If error "Extension connection timeout":**

Open Chrome and install the **Playwright MCP Bridge** extension:
`https://chromewebstore.google.com/detail/playwright-mcp-bridge/mmlmfjhmonkocbjadbfplnigmagldckm`

Ask user to install it, then retry:

```bash
playwright-cli open https://www.google.com --extension --headed
```

**Expected output:**

```
https://www.google.com is opened by playwright-cli with playwright chrome extension in headed mode
```

---

## Step 2 — Discord server and bot setup (via `playwright-cli` skill)

> **Warn user:** About to open Discord external websites. Confirm these are trusted before proceeding.

### 2a — Discord account and server

1. Ask user if they have a Discord account. If not, guide them to create one at `https://discord.com`.
2. Create a Discord server named **My OpenClaw**:
   Ref: `https://support.discord.com/hc/en-us/articles/204849977`
   Choose **Create My Own → For me and my friends**.

### 2b — Create Discord application and bot

Go to `https://discord.com/developers/applications` → **New Application** → name it `OpenClaw`.

1. **Bot tab** → set bot Username (e.g. `OpenClaw`).
2. Enable **Privileged Gateway Intents**:
   - ✅ Message Content Intent (required)
   - ✅ Server Members Intent (recommended)
3. Click **Reset Token** → copy and save the **Bot Token**.

### 2c — Generate OAuth2 invite URL and add bot to server

**OAuth2 tab → OAuth2 URL Generator:**

- Scopes: `bot`, `applications.commands`
- Bot Permissions:
  - ✅ View Channels
  - ✅ Send Messages
  - ✅ Read Message History
  - ✅ Embed Links
  - ✅ Attach Files

Copy the generated URL → open in browser → select **My OpenClaw** server → click **Continue**.

### 2d — Enable Developer Mode and collect IDs

In Discord app:
1. **User Settings → Advanced → Developer Mode**: ON
2. Right-click server icon → **Copy Server ID** → save as `DISCORD_SERVER_ID`
3. Right-click own avatar → **Copy User ID** → save as `DISCORD_USER_ID`

### 2e — Allow DMs from server members

Right-click server icon → **Privacy Settings** → toggle on **Direct Messages**.

### 2f — Save Discord bot info to `.env` (one password prompt)

```bash
core/bin/keys-safe-guard put_key_values \
  DISCORD_BOT_TOKEN=<bot-token> \
  DISCORD_SERVER_ID=<server-id> \
  DISCORD_USER_ID=<user-id>
```

Verify the values were saved correctly:

```bash
core/bin/keys-safe-guard get_key_value DISCORD_BOT_TOKEN DISCORD_SERVER_ID DISCORD_USER_ID
```

**Expected output:**

```
Discord Bot Token: [REDACTED — stored securely via keys-safe-guard]
Discord Server ID: <id>
Discord User ID:   <id>
```

---

## Step 3 — AWS account and key setup (via `playwright-cli` skill)

> **Warn user:** About to open AWS external website. Confirm it is trusted before proceeding.

1. Open `https://aws.amazon.com/` — check sign-in status.
   - Not signed in: ask user to sign in or create an account.
   - No account: guide user to sign up (free tier available; credit card required but no charge under free tier).

2. Create an AWS access key:
   - IAM → Users → select user → Security credentials → **Create access key** → select **CLI** use case.
   - Copy `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

3. Ask user which AWS region to use. Default: **Sydney, AU: `ap-southeast-2`**.

4. Save credentials to `.env` using `core/bin/keys-safe-guard` — one call, one password prompt:

   ```bash
   core/bin/keys-safe-guard put_key_values \
     AWS_ACCESS_KEY_ID=<value> \
     AWS_SECRET_ACCESS_KEY=<value> \
     AWS_REGION=<region> \
     DISABLE_AWS_API_MCP_SERVER=false
   core/bin/sync-mcp
   ```
5. Exec `core/bin/sync-mcp` and `core/bin/skill-install` to sync and install `aws-api` mcp skills defined at `config/mcp.json5`

**Expected output:**

```
AWS credentials saved to .env
AWS region: ap-southeast-2
aws-api MCP skill: enabled
```

---

## Step 4 — AWS EC2 instance provisioning (via `aws-ec2` skill)

Use the `aws-ec2` agent skill (backed by the AWS MCP server) for all EC2 operations.

### 4a — EC2 type selection

Show EC2 on-demand pricing at `https://aws.amazon.com/ec2/pricing/on-demand/` for the selected region.

**Recommended:** `t4g.small` — 2 vCPU, 2 GiB RAM, ARM Graviton2
- ~$0.0212/hr → ~$15.30/month (eligible for free tier — effectively $0 for 6 months on new accounts)
- 40% better price/performance vs T3 (ARM vs x86); ideal for OpenClaw (Node.js on Linux)

Ask user to confirm instance type or select another.

### 4b — Create VPC and networking

Using `aws-ec2` skill:

```
- Find latest Ubuntu 24.04 LTS ARM64 AMI for the selected region
- Create VPC: name=vpc-openclaw, CIDR=10.0.0.0/16
- Create subnet: name=subnet-openclaw, CIDR=10.0.1.0/24 (public subnet)
- Create internet gateway: igw-openclaw, attach to vpc-openclaw
- Create route table, add default route to igw-openclaw, associate with subnet-openclaw
- Create security group: name=sg-openclaw
  - Inbound: TCP port 22 (SSH) from 0.0.0.0/0
  - No other inbound ports (WebUI accessed via SSH tunnel only)
  - Outbound: all traffic allowed
```

### 4c — Launch EC2 instance

```
- Launch EC2 instance:
  - Name: openclaw-server
  - AMI: <latest Ubuntu 24.04 LTS ARM64>
  - Instance type: <user selected, default t4g.small>
  - VPC: vpc-openclaw, Subnet: subnet-openclaw
  - Security group: sg-openclaw
  - No key pair (will use EC2 Instance Connect or temp SSH key below)
  - Auto-assign public IP: enabled
  - Storage: 20 GiB gp3

- Monitor instance until status = running and status checks pass
```

**Expected output:**

```
EC2 Instance ID: i-xxxxxxxxxxxx
Public IP: x.x.x.x
State: running
```

---

## Step 5 — SSH key setup and EC2 connection

### 5a — Generate temp SSH key

```bash
mkdir -p .skillpilot/temp
# Remove existing key if present
rm -f .skillpilot/temp/openclaw-ec2-ssh .skillpilot/temp/openclaw-ec2-ssh.pub
# Generate new key
ssh-keygen -t ed25519 -f .skillpilot/temp/openclaw-ec2-ssh -N "" -C "openclaw-ec2-tmp"
```

### 5b — Push public key to EC2 instance

Use the `aws-ec2` skill to push the public key via EC2 Instance Connect:

```
aws ec2-instance-connect send-ssh-public-key \
  --instance-id <instance-id> \
  --instance-os-user ubuntu \
  --ssh-public-key file://.skillpilot/temp/openclaw-ec2-ssh.pub \
  --region <region>
```

> Note: EC2 Instance Connect temporary keys expire after 60 seconds — connect immediately after push.

### 5c — Add SSH profile to config/ssh.json5

Update or create `config/ssh.json5`, add profile `aws-ec2-tmp`:

```json5
{
  "profiles": {
    "aws-ec2-tmp": {
      "host": "<EC2_PUBLIC_IP>",
      "port": 22,
      "user": "ubuntu",
      "key": ".skillpilot/temp/openclaw-ec2-ssh",
      "timeoutMs": 60000
    }
  }
}
```

### 5d — Open SSH session

Use agent skill `terminal-open-session`:

```
target: ssh:aws-ec2-tmp
lifecycle: tmux
```

**Expected output:**

```
SSH profile aws-ec2-tmp added to config/ssh.json5
SSH session opened to EC2 instance (ubuntu@<IP>)
Session ID: <session-id>
```

---

## Step 6 — Install OpenClaw on EC2

Use the SSH session from Step 5 (`terminal-send-session-input`).

### 6a — Install using official installer script (no onboarding)

```bash
curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash -s -- --no-onboard
```

This handles Node 22+ detection/install, Git, and global npm install automatically.

After install, add to PATH if needed:

```bash
export PATH="$(npm prefix -g)/bin:$PATH"
echo 'export PATH="$(npm prefix -g)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify:

```bash
openclaw --version
```

### 6b — Create workspace directory

```bash
mkdir -p ~/.openclaw/workspace
```

---

## Step 7 — Write OpenClaw gateway configuration

Generate a random token:

```bash
node -e "const c=require('crypto');console.log(c.randomBytes(32).toString('hex'))"
```

Save the output as `OPENCLAW_GATEWAY_TOKEN`.

Write `~/.openclaw/openclaw.json` on the EC2 instance:

```json5
// ~/.openclaw/openclaw.json
{
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace",
      // Model will be set after Codex OAuth in Step 8
      model: { primary: "openai-codex/gpt-5.3-codex" },
    },
  },

  gateway: {
    mode: "local",
    port: 18789,
    bind: "loopback",   // SSH tunnel only — do NOT expose 18789 publicly
    auth: {
      mode: "token",
      token: "<OPENCLAW_GATEWAY_TOKEN>",
    },
    controlUi: { enabled: true },
  },

  channels: {
    discord: {
      enabled: true,
      token: "<DISCORD_BOT_TOKEN>",
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      guilds: {
        "<DISCORD_SERVER_ID>": {
          requireMention: false,
          users: ["<DISCORD_USER_ID>"],
        },
      },
    },
  },
}
```

Apply with:

```bash
openclaw doctor      # verify config is valid
```

---

## Step 8 — OpenAI Codex CLI OAuth

> **Note:** This step requires browser interaction on the user's local machine.
> The EC2 server is headless — the OAuth URL must be opened locally.

### 8a — Start the OAuth flow on EC2 (via SSH session)

```bash
openclaw models auth login --provider openai-codex
```

The CLI outputs an **authorization URL**.

### 8b — User opens URL in local browser

1. Copy the URL from the terminal output.
2. Open it in a local browser (Chrome/Firefox).
3. Sign in with the ChatGPT/OpenAI account that has a Codex subscription.
4. Click **Authorize**.

The CLI captures the callback automatically (it polls for the token). Wait until the CLI confirms:
```
✓ Authenticated with openai-codex
```

### 8c — Verify Codex auth

```bash
openclaw models status
```

Expect to see `openai-codex` listed as authenticated.

**Expected output:**

```
Provider: openai-codex  Status: authenticated
```

---

## Step 9 — Run OpenClaw as a persistent background service (systemd)

Create a systemd service on the EC2 instance:

```bash
sudo tee /etc/systemd/system/openclaw.service > /dev/null <<'EOF'
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/openclaw gateway
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

> If `which openclaw` returns a different path (e.g. `/home/ubuntu/.npm-global/bin/openclaw`),
> update `ExecStart` accordingly.

Verify service is running:

```bash
sudo systemctl status openclaw
openclaw status
openclaw health
```

**Expected output:**

```
openclaw.service: active (running)
Gateway: running on ws://127.0.0.1:18789
```

---

## Step 10 — Discord bot pairing

After the gateway is running and Discord is configured:

1. **In the Discord app**, DM your OpenClaw bot with any message.
2. The bot responds with a **pairing code**.
3. On the EC2 instance (via SSH), approve the pairing:

```bash
openclaw pairing list discord
openclaw pairing approve discord <CODE>
```

> Pairing codes expire after 1 hour.

### 10b — Add server to guild workspace (guild channel mode)

To enable bot responses in your server channels (not just DMs):

```bash
openclaw config set channels.discord.guilds.<DISCORD_SERVER_ID>.requireMention false --json
```

Test by sending a message in any Discord channel — the bot should respond.

---

## Step 11 — Access OpenClaw WebUI via SSH tunnel (via `playwright-cli` skill)

### 11a — Create SSH tunnel (local → EC2 port 18789)

Use agent skill `terminal-forward-remote-to-local`:

```
target: ssh:aws-ec2-tmp
remotePort: 18789
localPort: 18789
```

Or manually:

```bash
ssh -N -L 18789:127.0.0.1:18789 ubuntu@<EC2_PUBLIC_IP> -i .skillpilot/temp/openclaw-ec2-ssh
```

### 11b — Open WebUI

Use agent skill `playwright-cli open http://127.0.0.1:18789 --extension --headed`

Authenticate with the gateway token from Step 7.

**Expected output:**

```
OpenClaw local access URL: http://127.0.0.1:18789
Gateway token: <OPENCLAW_GATEWAY_TOKEN>
```

---

## Step 12 — Wrap-up

Report final status:

```
EC2 Instance:    i-xxxxxxxxxxxx (openclaw-server)
Public IP:       x.x.x.x
OpenClaw:        running (systemd, auto-restart enabled)
Gateway:         loopback:18789 (token auth)
Provider:        openai-codex (authenticated via OAuth)
Discord:         connected (bot online, guild allowlist configured)
WebUI access:    SSH tunnel → http://127.0.0.1:18789
```

Ask user what to do next:

1. **Leave running** — OpenClaw stays online 24/7 (~$15/month)
2. **Stop EC2** — `aws ec2 stop-instances --instance-ids <id>` (no charge while stopped)
3. **Terminate EC2** — `aws ec2 terminate-instances --instance-ids <id>` (deletes everything)

---

## Quick Reference — Key CLI Commands

```bash
# Gateway control
openclaw gateway              # start gateway (foreground)
openclaw status               # check gateway status
openclaw health               # health check
openclaw doctor               # config validation and diagnostics

# Config
openclaw config get <key>
openclaw config set <key> <value> --json

# Models / auth
openclaw models status
openclaw models auth login --provider openai-codex

# Discord
openclaw pairing list discord
openclaw pairing approve discord <CODE>
openclaw channels status --probe

# Systemd
sudo systemctl start openclaw
sudo systemctl stop openclaw
sudo systemctl restart openclaw
sudo journalctl -u openclaw -f
```

---

## Tool and Skill Selection Reference

| Step                              | Skill / Tool                         |
| --------------------------------- | ------------------------------------ |
| Browser automation                | `playwright-cli`                     |
| AWS account / key setup           | `playwright-cli` (browser)           |
| EC2 provisioning                  | `aws-ec2` skill                      |
| SSH key push                      | `aws-ec2` (EC2 Instance Connect)     |
| SSH session management            | `terminal-open-session` (tmux)       |
| SSH tunnel (WebUI)                | `terminal-forward-remote-to-local`   |
| Remote commands                   | `terminal-send-session-input`        |
| Env/key management                | `core/bin/keys-safe-guard`           |
