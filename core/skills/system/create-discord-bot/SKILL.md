---
name: create-discord-bot
description: Create a Discord server and bot application with browser automation, collect the bot token, server ID, and user ID, then save credentials to .env via keys-safe-guard. Skip if OPENCLAW_DISCORD_BOT_TOKEN is already set. Use for any project that needs a Discord bot.
---

# Create Discord Bot

Automate as much of the Discord setup flow as possible through the official Discord web UI,
then securely save the bot token, server ID, and user ID to `config/.env`.

## When to Use This Skill

- A Discord bot token is needed for any project
- Discord bot token is missing from `config/.env`
- User needs to create a new Discord application and bot
- The user wants the Discord website flow handled mostly by AI, with manual input only for login or anti-bot gates

## Your Roles in This Skill

- **SysOps Engineer**: Guide browser-based setup and save credentials securely
- **Security Engineer**: Store token via keys-safe-guard only — never print full token value

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Preconditions

- `playwright-cli` is ready (run skill `init-playwright` if unsure)
- Only use official Discord domains: `https://discord.com` and `https://discord.com/developers`

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

### Step 3: Automation mode

Default to this execution model:

1. AI opens the official Discord pages and performs the browser steps.
2. The user only intervenes when Discord requires:
   - login
   - email verification
   - 2FA
   - CAPTCHA / anti-bot checks
   - final human confirmation dialogs that automation cannot complete
3. After each user-only checkpoint, continue the browser flow automatically.

Do not ask the user to manually click through routine setup pages when AI can do it.

### Step 4: Ensure Discord account and server

Open Discord in a headed browser:

```bash
playwright-cli open https://discord.com/app --extension --headed
```

AI should:
1. Wait for the user to sign in if Discord shows the login screen.
2. Detect whether a suitable server already exists.
3. If no server exists, create one automatically:
   - click **+**
   - choose **Create My Own**
   - choose **For me and my friends**
   - name it clearly, for example `OpenClaw` or the project name

Only ask the user for manual help if Discord blocks one of those steps.

### Step 5: Create bot application in the Developer Portal

```
playwright-cli open https://discord.com/developers/applications --extension --headed
```

AI should perform:
1. Wait for the user to sign in if the Developer Portal requires login.
2. Click **New Application** → enter a clear name → **Create**
3. Open the **Bot** tab and create the bot user if Discord shows an add/create bot button.
4. Confirm or set the bot username.
5. Enable **Privileged Gateway Intents**:
   - ✅ Message Content Intent (required)
   - ✅ Server Members Intent (recommended)
6. Click **Reset Token** and confirm the reset dialog.
7. Capture the token immediately.

Token handling rules:
- Prefer reading or copying the token directly from the page via automation.
- Never echo the full token in chat, logs, or summaries.
- If Discord prevents automated token capture, ask the user to paste it privately as a fallback.

### Step 6: Generate OAuth2 invite URL and add bot to server

AI should perform in Developer Portal:
1. Open **OAuth2** → **URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select bot permissions: View Channels, Send Messages, Read Message History, Embed Links, Attach Files
4. Open the generated invite URL

Then continue the invite flow:
1. Select the created or chosen server
2. Click **Continue**
3. Click **Authorize**

If Discord shows CAPTCHA or extra anti-abuse verification, pause and ask the user to complete only that step.

### Step 7: Enable Developer Mode and collect IDs

AI should try to collect IDs with the least manual work:
1. In Discord web app, open **User Settings** → **Advanced** → enable **Developer Mode**
2. Capture the server ID from the selected server by using Discord’s copy-ID UI if accessible
3. Capture the user ID from the signed-in user profile/avatar menu if accessible

If Discord blocks automated copy or context-menu access, ask the user only for the missing values:
1. Right-click server icon → **Copy Server ID**
2. Right-click own avatar → **Copy User ID**

### Step 8: Allow DMs from server members

Right-click server icon → **Privacy Settings** → toggle **Direct Messages** ON.

### Step 9: Save credentials to .env

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

### Step 10: Safe guard behavior

When `config/.env` is protected by key safe guard:

- Interactive terminal run:
  - `core/bin/keys-safe-guard ...` will use terminal `sudo`
- Python/background process in a GUI desktop session:
  - `core/bin/keys-safe-guard ...` will automatically open a native GUI permission dialog
- Python/background process without a GUI desktop session:
  - it cannot prompt for a password interactively
  - tell the user to either:
    - configure passwordless sudo for this machine, or
    - disable safe guard before the automated flow writes secrets

Do not claim the command is stuck. Wait for the GUI dialog or terminal sudo prompt to be completed.

### Step 11: Report result

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
- **User-only checkpoints**: login, CAPTCHA, email verification, and 2FA must be completed by the user when Discord requires them
- **safe guard without GUI**: background Python calls cannot type a sudo password; use a desktop GUI session, configure passwordless sudo, or disable safe guard first
