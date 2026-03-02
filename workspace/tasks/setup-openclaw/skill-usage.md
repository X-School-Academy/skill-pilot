# Skill Usage — Setup OpenClaw on AWS EC2

How to run the 7 agent skills in sequence to complete the full setup defined in `requirement.md`.

Each skill is self-contained with a skip condition — re-run any skill safely if a step was
interrupted. Pass outputs from one skill as inputs to the next.

---

## Execution Order

```
1. init-playwright
2. create-discord-bot
3. enable-aws-cli
        ↓
4. setup-aws-ec2          ← needs: AWS region from step 3
        ↓
5. connect-ec2-ssh        ← needs: instance ID + public IP from step 4
        ↓
6. openclaw-install-on-ec2  ← needs: SSH session ID from step 5
                              needs: Discord token from step 2
        ↓
7. openclaw-connect-tunnel  ← needs: public IP + gateway token from step 6
```

Steps 1, 2, and 3 can run in any order or in parallel — they have no interdependencies.

---

## Step 1 — `init-playwright`

**Prompt:**
> Use skill `init-playwright` to verify playwright-cli is ready.

**What it does:** Installs playwright-cli and Chrome if missing, activates the MCP Bridge extension.

**Output to note:** confirmation that playwright-cli is ready and the version.

**Skip if:** playwright-cli already works — the skill self-checks and exits early.

---

## Step 2 — `create-discord-bot`

**Prompt:**
> Use skill `create-discord-bot` to create a Discord bot for OpenClaw. Save the bot token,
> server ID, and user ID to config/.env.

**What it does:** Opens the Discord Developer Portal, guides creation of a bot application,
collects the bot token + server ID + user ID, saves all three to `config/.env` via keys-safe-guard.

**Output to note:**
- `DISCORD_SERVER_ID` and `DISCORD_USER_ID` (shown in output — safe to copy)
- `DISCORD_BOT_TOKEN` (confirmed set, value not shown)

**Skip if:** `DISCORD_BOT_TOKEN` is already non-empty in `.env`.

---

## Step 3 — `enable-aws-cli`

**Prompt:**
> Use skill `enable-aws-cli` to set up AWS credentials for region ap-southeast-2
> and enable the aws-api MCP skill.

**What it does:** Opens AWS Console, guides IAM access key creation, saves keys + region
to `.env`, syncs MCP.

**Output to note:** AWS region (used in steps 4 and 5).

**Skip if:** `AWS_ACCESS_KEY_ID` and `AWS_REGION` are already set.

---

## Step 4 — `setup-aws-ec2`

**Prompt:**
> Use skill `setup-aws-ec2` to provision an EC2 instance named `openclaw-server` with
> instance type `t4g.small`. Use region from .env. Allow SSH only (port 22).

**What it does:** Creates VPC, subnet, internet gateway, SSH-only security group, and launches
an Ubuntu 24.04 ARM instance. Waits for running state.

**Output to note (pass to step 5):**
```
EC2 Instance ID:  i-xxxxxxxxxxxx
Public IP:        x.x.x.x
Region:           ap-southeast-2
```

**Skip if:** instance `i-xxxxxxxxxxxx` is already in running state.

---

## Step 5 — `connect-ec2-ssh`

**Prompt:**
> Use skill `connect-ec2-ssh` to connect to EC2 instance `<instance-id>` at `<public-ip>`
> in region `<region>`. Use profile name `ec2-tmp`.

**What it does:** Generates a temp ed25519 key, pushes it via EC2 Instance Connect,
adds profile `ec2-tmp` to `config/ssh.json5`, opens a tmux SSH session.

**Output to note (pass to step 6):**
```
Session ID:   <session-id>
SSH profile:  ec2-tmp
```

**Skip if:** a tmux session to the instance is still alive.

---

## Step 6 — `openclaw-install-on-ec2`

**Prompt:**
> Use skill `openclaw-install-on-ec2` to install OpenClaw on EC2 using SSH session `<session-id>`.
> The Discord bot token, server ID, and user ID are already in config/.env.
> I have a ChatGPT Codex subscription for the OAuth step.
> Show me the gateway token when done.

**What it does:**
1. Installs OpenClaw via the official installer script
2. Generates a random gateway token
3. Writes `~/.openclaw/openclaw.json` with gateway config, Codex model, and Discord channel
4. Runs `openclaw models auth login --provider openai-codex` → shows URL for user to open locally
5. Sets up systemd service (auto-restart on reboot)
6. Pairs the Discord bot (user DMs the bot → approves pairing code on EC2)

**Human-in-the-loop steps:**
- Open the Codex OAuth URL in local browser and authorize
- DM the Discord bot and copy the pairing code back to the skill

**Output to note (pass to step 7):**
```
Gateway token:  <64-char hex — save this>
Public IP:      x.x.x.x
```

**Skip if:** `openclaw status` responds on EC2 — ask user whether to skip or reinstall.

---

## Step 7 — `openclaw-connect-tunnel`

**Prompt:**
> Use skill `openclaw-connect-tunnel` to create an SSH tunnel to EC2 at `<public-ip>`
> using key `.skillpilot/temp/ec2-tmp-ssh`, then open the WebUI in the browser.
> Gateway token: `<token from step 6>`.

**What it does:** Forwards local port 18789 → EC2:18789 via SSH tunnel, opens
`http://127.0.0.1:18789` in Chrome via playwright-cli, authenticates with the gateway token.

**Skip if:** `curl http://127.0.0.1:18789/health` returns a valid response.

**Final output:**
```
OpenClaw WebUI:   http://127.0.0.1:18789
Health check:     OK
Discord:          connected
Provider:         openai-codex (authenticated)
```

---

## Handling Interruptions

If any step fails or is interrupted, re-run the same skill — each has a skip condition that
detects already-completed work. The key outputs to carry forward manually are:

| Produced by | Value | Needed by |
|-------------|-------|-----------|
| step 4 | EC2 instance ID | step 5 |
| step 4 | EC2 public IP | steps 5, 7 |
| step 5 | SSH session ID | step 6 |
| step 6 | gateway token | step 7 |

If the SSH key expires (EC2 Instance Connect keys last 60 seconds at push time, but the key file
persists locally), re-run step 5 — it pushes a new key and opens a fresh session.

---

## Teardown

After the session is done, ask the user:

```
1. Leave running    — openclaw stays online 24/7 (~$15/month)
2. Stop instance    — aws ec2 stop-instances --instance-ids <id> --region <region>
                      (no charge while stopped; data preserved)
3. Terminate        — aws ec2 terminate-instances --instance-ids <id> --region <region>
                      (deletes instance and storage)
```
