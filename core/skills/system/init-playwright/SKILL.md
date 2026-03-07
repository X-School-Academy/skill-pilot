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

Treat this as an immediate readiness check:

- If it returns quickly with `Browser \`default\` opened with pid ...`, the browser bridge is ready.
- If it does **not** return immediately, assume the extension is missing or waiting for user permission.

In that case, instruct the user to install or approve the **Playwright MCP Bridge** extension, then continue with Step 3.

### Step 3: Check any errors

**If get error, Chrome is not installed**

```bash
pnpm exec playwright install chrome # install the official branded Google Chrome browser
```

**If the open command does not return immediately, or if "Extension connection timeout" appears:**

Warn user: "About to open Chrome Web Store — this is a trusted Google site."

Ask user to open Chrome and install the **Playwright MCP Bridge** extension by url below:
```
https://chromewebstore.google.com/detail/playwright-mcp-bridge/mmlmfjhmonkocbjadbfplnigmagldckm
```

After install, ask the user to paste:

```bash
PLAYWRIGHT_MCP_EXTENSION_TOKEN=token-string
```

If the user provides a token, verify it first without saving anything:

```bash
PLAYWRIGHT_MCP_EXTENSION_TOKEN=token-string playwright-cli open --extension --headed
```

The verification is successful only if the command responds immediately with text like:

```text
Browser `default` opened with pid 44554.
```

If verification succeeds, use the `key-safe` skill to save `PLAYWRIGHT_MCP_EXTENSION_TOKEN` into `config/.env`.

If the token fails verification, do not save it. Tell the user the token is invalid and ask for a new token.

If the user does not want to paste a token, tell them they can manually approve the extension every time browser automation starts.

Repeat until `playwright-cli open --extension --headed` works immediately without waiting for approval.

### Step 4: Report result of the browser opened

```bash
playwright-cli list
```

the output should be 

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

If user requested file output, write the same content to the specified path.

## Common Issues

- **pnpm not found**: use `npm install -g @playwright/cli@latest` instead
- **Extension keeps timing out**: ensure the MCP Bridge extension is enabled in Chrome and not paused
- **No token provided**: browser automation can still work, but the user may need to manually approve the extension each time
- **Chrome opens but page doesn't load**: check network connectivity
