---
name: init-playwright
description: Initialize and verify playwright-cli with Chrome and the Playwright MCP Bridge extension. Check and skip if already ready. Use before any browser automation task.
---

# Init Playwright CLI

Verify that `playwright-cli`, Chrome, and the Playwright MCP Bridge extension are ready
before any browser automation is attempted.

## When to Use This Skill

- Any task that requires browser automation via playwright-cli
- playwright-cli may not be installed or Chrome may be missing
- The MCP Bridge extension may not be active

## Your Roles in This Skill

- **SysOps Engineer**: Install and validate playwright-cli and Chrome
- **QA Engineer**: Confirm the browser extension bridge is active end-to-end

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Other Agent Skills Required

- `key-safe`
- `playwright-cli`

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (what was checked, what is ready, and any blocking issue) so downstream agents can safely continue.

## Instructions

### Step 1: Check if playwright-cli is installed

```bash
playwright-cli --version
```

If the command is not found:

```bash
pnpm install -g @playwright/cli@latest
playwright-cli --version
```

### Step 2: Test browser + extension bridge

```bash
playwright-cli open --extension --headed
```

Treat this as an **initialization flow**, not a blocking foreground command:

- Start it in a background process.
- Do **not** wait for the command to sit there until timeout.
- This init command is only for extension setup. Once setup is complete, normal browser automation should use direct commands such as `playwright-cli open --extension --headed`.

Interpret the result as follows:

- If it returns quickly with `Browser \`default\` opened with pid ...`, the browser bridge is ready.
- If it returns within about 10 seconds with `Extension connection timeout. Make sure the "Playwright MCP Bridge" extension is installed.`, go to Step 3 and instruct the user to install the Chrome extension.
- If it stays open for more than about 10 seconds with no return, assume the browser is waiting for permission and is showing the extension token page. Go to Step 3 and instruct the user to copy-paste the `PLAYWRIGHT_MCP_EXTENSION_TOKEN` value.
- If you get an error that Chrome is not installed, then go to Step 3 to install Google Chrome.

### Step 3: Check any errors

**If you get an error that Chrome is not installed**

```bash
pnpm exec playwright install chrome # install the official branded Google Chrome browser
```

Once Chrome is installed, go to Step 2 and test the browser + extension bridge.

**If the Chrome extension is not installed:**

Ask the user to open Chrome and install the **Playwright MCP Bridge** extension using the URL below:
```
https://chromewebstore.google.com/detail/playwright-mcp-bridge/mmlmfjhmonkocbjadbfplnigmagldckm
```

Ask the user to confirm once the installation is complete, then go to Step 2 and test the browser + extension bridge.

If the extension is ready and waiting for authentication, give the user two options:

1. Ask the user to copy and paste the token, then save it for automatic authentication.
2. Ask the user to click the connect button for one-time approval.

The token format shown on the Chrome extension screen is:
```bash
PLAYWRIGHT_MCP_EXTENSION_TOKEN=xxxxxxxx_xxxxxxx_xxx_xxxxxxxxxxxxxxxxxxxxxx
```

If the user provides a token, kill the background `playwright-cli open --extension --headed` process, then verify it without saving anything:

```bash
PLAYWRIGHT_MCP_EXTENSION_TOKEN=token-string playwright-cli open --extension --headed
```

The verification is successful only if the command responds immediately with text like:

```text
Browser `default` opened with pid 44554.
```

If verification succeeds, use the `key-safe` skill to save `PLAYWRIGHT_MCP_EXTENSION_TOKEN` into `config/.env`.

After the token has been verified and saved, future browser automation should run normally with direct commands such as:

```bash
playwright-cli open --extension --headed
```

No manual approval should be needed unless the token is changed or becomes invalid.

If the token fails verification, do not save it. Tell the user the token is invalid and ask for a new token.

If the user does not want to paste a token, tell them they can manually approve the extension each time browser automation starts.

Repeat until `playwright-cli open --extension --headed` works immediately without waiting for approval.

### Step 4: Report result of the browser opened

```bash
playwright-cli list
```

The output should be:

```markdown
### Browsers
- default:
  - status: open
  - browser-type: chrome
  - user-data-dir: <in-memory>
  - headed: true
```

Output result as plain text, say "Default Google Chrome has been opened and is ready to use. Open any web URL using: `playwright-cli goto URL` by agent skill `playwright-cli`." If the user asked to save it to a file, write it there.

## Output

Plain text result shown to user (example):

```
Playwright CLI: ready
Chrome: Opened and ready to use
MCP Bridge extension: connected
Token setup: verified and saved with key-safe, or manual approval required
Open any web URL using: `playwright-cli goto URL` by agent skill `playwright-cli`
```

If the user requested file output, write the same content to the specified path.

## Common Issues

- **pnpm not found**: use `npm install -g @playwright/cli@latest` instead
- **Extension keeps timing out**: ensure the MCP Bridge extension is enabled in Chrome and not paused
- **No token provided**: browser automation can still work, but the user may need to manually approve the extension each time
- **Chrome opens but page doesn't load**: check network connectivity
