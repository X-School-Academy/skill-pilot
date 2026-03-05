---
name: init-playwright
description: Initialize and verify playwright-cli with Chrome and the Playwright MCP Bridge extension. Check and skip if already ready. Use before any browser automation task.
---

# Init Playwright CLI

Verify that `playwright-cli`, Chrome, and the Playwright MCP Bridge extension are all working
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

## Preconditions

None — this skill is self-contained.

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (what was checked, what is ready, and any blocking issue) so downstream agents can safely continue.

## Skip Condition

Run the test command directly. If it succeeds, skip remaining install steps and report ready.

```bash
playwright-cli --version
```

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

### Step 2: Check if Chrome is installed

```bash
playwright install chrome
```

(Safe to re-run — skips if already installed.)

### Step 3: Test browser + extension bridge

```bash
playwright-cli open https://www.google.com --extension --headed
```

**If "Extension connection timeout" error appears:**

Warn user: "About to open Chrome Web Store — this is a trusted Google site."

Ask user to open Chrome and install the **Playwright MCP Bridge** extension:
```
https://chromewebstore.google.com/detail/playwright-mcp-bridge/mmlmfjhmonkocbjadbfplnigmagldckm
```

Once installed, retry the open command. Repeat until the browser opens successfully.

### Step 4: Report result

Capture the playwright-cli version:
```bash
playwright-cli --version
```

Output result as plain text. If the user asked to save it to a file, write it there.

## Output

Plain text result shown to user (example):

```
Playwright CLI: ready
Version: 1.x.x
Chrome: installed
MCP Bridge extension: connected
```

If user requested file output, write the same content to the specified path.

## Common Issues

- **pnpm not found**: use `npm install -g @playwright/cli@latest` instead
- **Extension keeps timing out**: ensure the MCP Bridge extension is enabled in Chrome and not paused
- **Chrome opens but page doesn't load**: check network connectivity
