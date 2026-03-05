---
name: create-discord-bot
description: Create a Discord server and bot application, collect bot token, server ID, and user ID, then save credentials to .env via keys-safe-guard. Skip if OPENCLAW_DISCORD_BOT_TOKEN is already set. Use for any project that needs a Discord bot.
---

# Create Discord Bot

Guide the user through creating a Discord server and bot application via the Developer Portal,
then securely save the bot token, server ID, and user ID to `config/.env`.

## When to Use This Skill

- A Discord bot token is needed for any project
- Discord bot token is missing from `config/.env`
- User needs to create a new Discord application and bot

## Your Roles in This Skill

- **SysOps Engineer**: Guide browser-based setup and save credentials securely
- **Security Engineer**: Store token via keys-safe-guard only — never print full token value

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Preconditions

- `playwright-cli` is ready (run skill `init-playwright` if unsure)

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (created/reused bot status, which IDs were captured, and whether secrets were saved) so downstream agents can safely continue.

## Skip Condition

Check if the token is already saved:

```bash
core/bin/keys-safe-guard get_key_value OPENCLAW_DISCORD_BOT_TOKEN
```

If the output shows a non-empty value, ask user whether to skip or replace it.

## Instructions

### Step 1: Check existing token

```bash
core/bin/keys-safe-guard get_key_value OPENCLAW_DISCORD_BOT_TOKEN 2>/dev/null || true
```

If set and user confirms to keep it, skip.

### Step 2: Warn user about external site

> **Security notice:** About to open discord.com and discord.com/developers.
> Confirm these are trusted before proceeding.

### Step 3: Ensure Discord account and server

1. Ask: "Do you have a Discord account?"
   - If no: guide user to `https://discord.com` to create one.
2. Ask: "Do you already have a Discord server for this bot?"
   - If no: guide user to create one:
     - Open `https://discord.com/app` → click **+** → **Create My Own** → **For me and my friends**
     - Name it (e.g. `My OpenClaw` or any name the user chooses)

### Step 4: Create bot application (via playwright-cli)

```
playwright-cli open https://discord.com/developers/applications --extension --headed
```

Guide user through:
1. Click **New Application** → enter a name → **Create**
2. **Bot** tab → confirm or set the bot username
3. Enable **Privileged Gateway Intents**:
   - ✅ Message Content Intent (required)
   - ✅ Server Members Intent (recommended)
4. Click **Reset Token** → **Yes, do it!** → copy the token immediately

Ask user to paste the token privately. Do not display it back.

### Step 5: Generate OAuth2 invite URL and add bot to server

In Developer Portal:
1. **OAuth2** tab → **OAuth2 URL Generator**
2. Scopes: `bot`, `applications.commands`
3. Bot Permissions: View Channels, Send Messages, Read Message History, Embed Links, Attach Files
4. Copy the generated URL

Open the invite URL in browser → select the server → **Continue** → **Authorize**.

### Step 6: Enable Developer Mode and collect IDs

In Discord app:
1. **User Settings** → **Advanced** → enable **Developer Mode**
2. Right-click server icon → **Copy Server ID**
3. Right-click own avatar → **Copy User ID**

Ask user to provide both IDs.

### Step 7: Allow DMs from server members

Right-click server icon → **Privacy Settings** → toggle **Direct Messages** ON.

### Step 8: Save credentials to .env

```bash
core/bin/keys-safe-guard put_key_values \
  OPENCLAW_DISCORD_BOT_TOKEN=<bot-token> \
  OPENCLAW_DISCORD_SERVER_ID=<server-id> \
  OPENCLAW_DISCORD_USER_ID=<user-id>
```

Verify Server ID and User ID were saved (safe to display):
```bash
core/bin/keys-safe-guard get_key_value OPENCLAW_DISCORD_SERVER_ID OPENCLAW_DISCORD_USER_ID
```

Confirm token is set without printing its value:
```bash
core/bin/keys-safe-guard get_key_value OPENCLAW_DISCORD_BOT_TOKEN | grep -c "OPENCLAW_DISCORD_BOT_TOKEN=." \
  && echo "OPENCLAW_DISCORD_BOT_TOKEN: set" || echo "OPENCLAW_DISCORD_BOT_TOKEN: MISSING"
```

### Step 9: Report result

Output result as plain text. If the user asked to save it to a file, write it there.

## Output

Plain text result shown to user:

```
Discord bot:      created and configured
Bot token:        saved to config/.env (not shown)
Server ID:        <id>
User ID:          <id>
DM policy:        enabled
```

## Common Issues

- **"Missing Access"** when adding bot: ensure correct server is selected in the invite flow
- **Token only shown once**: must be copied immediately after Reset Token — it cannot be retrieved again
- **Privileged intents not visible**: scroll down on the Bot page in Developer Portal
