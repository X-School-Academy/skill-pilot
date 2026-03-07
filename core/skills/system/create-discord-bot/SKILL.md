---
name: create-discord-bot
description: Create a Discord server and bot application with browser automation, collect the bot token, server ID, and user ID, then save credentials to .env via the key-safe skill. Skip if OPENCLAW_DISCORD_BOT_TOKEN is already set. Use for any project that needs a Discord bot.
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
- **Security Engineer**: Store token only through skill `key-safe` and never print the full token value

## Other Agent Skills Required

- `key-safe`
- `playwright-cli`

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Preconditions

- `playwright-cli` is ready (run skill `init-playwright` if not installed)
- Only use official Discord domains: `https://discord.com` and `https://discord.com/developers`

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (created/reused bot status, which IDs were captured, and whether secrets were saved) so downstream agents can safely continue.

## Skip Condition

Check if the token is already saved:

- Use skill `key-safe` to get `OPENCLAW_DISCORD_BOT_TOKEN`.

If the output shows a non-empty value, ask user whether to skip or replace it.

## Instructions

Only ask the user for manual help if you cannot finish a step or need to verify as a human.

### Step 1: Check existing token

Use skill `key-safe` to get `OPENCLAW_DISCORD_BOT_TOKEN`.

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
playwright-cli goto https://discord.com/channels/@me
```

AI should:
1. Wait for the user to sign in if Discord shows the login screen.
2. Detect whether a suitable server already exists.
  - the server name contains `openclaw` or `skillpilot` depending on the workflow purpose
  - the user has admin permission: open the server by clicking the server name in the left top to see if having `Server Settings` menu
  - then ask user to conform the server name or create a new one
3. If no server exists or need to create a new one, create one automatically:
   - ask user to confirm to create a new server, or user tell to use any exist server
   - click `Add a Server` button in the left tool bar
   - choose **Create My Own**
   - choose **For me and my friends**
   - name it clearly, default `OpenClaw` or `SkillPilot` depending on the workflow purpose

### Step 5: Create bot application in the Developer Portal

```bash
playwright-cli goto https://discord.com/developers/applications
```

AI should perform:
1. Wait for the user to sign in if the Developer Portal requires login.
2. Click `skip` in the onboard screen if have, and go to the developer portal directly.
3. Click **New Application** → enter a clear name (`OpenClaw` or `SkillPilot` depending on the context) → **Create** (Tick the acccept terms checkbox first on behalf of the user)
4. Open the **Bot** tab under overview 
  - create a new bot (by the `create` button in the top right) if the current bot is not avaible
  - Confirm or set the bot username.
5. Scroll to **Privileged Gateway Intents**:
   - ✅ Message Content Intent (required)
   - ✅ Server Members Intent (recommended)
7. Click **Reset Token** and confirm the reset dialog (Ask user to verify if need).
8. Capture the token immediately.

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
1. Right-click server icon → **Copy Server ID** or find from url `https://discord.com/channels/{SERVER_ID}/{CHANNEL_ID}`
2. Right-click own avatar → **Copy User ID**

### Step 8: Allow DMs from server members

Right-click server icon → **Privacy Settings** → toggle **Direct Messages** ON if it is OFF

### Step 9: Save credentials to .env

Use skill `key-safe` to save:
- `OPENCLAW_DISCORD_BOT_TOKEN=<bot-token>`
- `OPENCLAW_DISCORD_SERVER_ID=<server-id>`
- `OPENCLAW_DISCORD_USER_ID=<user-id>`

Then use skill `key-safe` to get:
- `OPENCLAW_DISCORD_SERVER_ID`
- `OPENCLAW_DISCORD_USER_ID`

Confirm the token is set without printing its value. Report only whether `OPENCLAW_DISCORD_BOT_TOKEN` is present.

### Step 10: Safe guard behavior

When `config/.env` is protected by key safe guard:

- Interactive terminal run:
  - invoke skill `key-safe`; that skill handles the correct elevation flow
- Python/background process in a GUI desktop session:
  - invoke skill `key-safe`; it should use the native GUI permission dialog behavior
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
