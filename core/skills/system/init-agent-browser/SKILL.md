---
name: init-agent-browser
description: Initialize and verify AI Agent for web browser setup with Chrome for browser automation.
---

# Init Agent Browser

Verify that `agent-browser` is installed and configure the correct Chrome connection
method for the current environment before any browser automation is attempted.

## When to Use This Skill

- Any task that requires browser automation via agent-browser
- agent-browser may not be installed or Chrome may be missing
- The environment-specific connection has not yet been configured

## Your Roles in This Skill

- **SysOps Engineer**: Install and validate agent-browser and Chrome
- **QA Engineer**: Confirm the browser connection is working end-to-end

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if you have more roles}, I will {action description}

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (what was checked, what is ready, and any blocking issue) so downstream agents can safely continue.

## Instructions

### Step 1: Check if agent-browser is installed

```bash
agent-browser --version
```

If the command is not found, install it:

```bash
pnpm install -g agent-browser
agent-browser --version
```

### Step 2: Check environment

Detect the current environment and configure the correct connection method.

#### Detect environment

Check in this order:

1. **Windows WSL** — run `uname -r` and check if the output contains `microsoft` or `WSL`
2. **macOS** — run `uname` and check if output is `Darwin`
3. **Linux with GUI** — check if `DISPLAY` or `WAYLAND_DISPLAY` is set, or if `DISPLAY` can be detected
4. **Docker or Linux without GUI** — otherwise (no display available)

See `references/` for platform-specific details.

---

#### Windows WSL

Refer to [references/windows-wsl.md](references/windows-wsl.md).

Ask the user to copy the Windows binary to their Windows host:

```
extensions/chrome-devtool-proxy/bin/chrome-devtool-proxy-windows-amd64.exe
```

Ask the user to run it on the Windows host with:

```
chrome-devtool-proxy-windows-amd64.exe
```

The proxy will print the host IP and the full connect command, for example:

```
[proxy] connect from remote: agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
```

Once the user provides the cdp ws URL shown in the proxy output, update `dev-swarm/user_preferences.md` to record:

```
Browser automation command: agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
```

---

#### macOS

Refer to [references/mac.md](references/mac.md).

Update `dev-swarm/user_preferences.md` to record:

```
Browser automation command: agent-browser --auto-connect open URL
```

---

#### Linux with GUI

Refer to [references/linux-gui.md](references/linux-gui.md).

Update `dev-swarm/user_preferences.md` to record:

```
Browser automation command: agent-browser --auto-connect open URL
```

---

#### Docker or Linux without GUI

Refer to [references/linux-no-gui.md](references/linux-no-gui.md).

Determine the correct binary for the host platform. Available binaries are under:

```
extensions/chrome-devtool-proxy/bin/
```

Ask the user to copy the appropriate binary to their host machine and run it:

```bash
./chrome-devtool-proxy-<platform>
```

The proxy will print the host IP and the full connect command, for example:

```
[proxy] connect from remote: agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
```

Once the user provides the cdp ws URL shown in the proxy output, update `dev-swarm/user_preferences.md` to record:

```
Browser automation command: agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
```

---

### Step 3: Test with agent-browser

Using the connection command recorded in `dev-swarm/user_preferences.md`, open https://www.google.com:

```bash
# macOS / Linux with GUI
agent-browser --auto-connect open https://www.google.com

# Windows WSL / Docker / Linux without GUI
agent-browser open https://www.google.com --cdp ws://<cdp_ws_url>
```

Then take a snapshot to confirm the page loaded:

```bash
agent-browser snapshot -i
```

If no errors occur, proceed to Step 5 (Report result).

### Step 4: Handle errors

If the test in Step 3 fails, Chrome may not have remote debugging enabled.

Ask the user to enable remote debugging in Chrome using the platform-appropriate command:

**Linux:**

```bash
google-chrome chrome://inspect/#remote-debugging
```

**macOS:**

```bash
open -a "Google Chrome" chrome://inspect/#remote-debugging
```

**Windows:**

```bash
start chrome chrome://inspect/#remote-debugging
```

If Chrome is not installed, run:

```bash
agent-browser install
```

This installs a Chrome build managed by agent-browser. Then retry Step 3.

### Step 5: Report result

Output result as plain text, say "agent-browser is ready. Use the configured command from `dev-swarm/user_preferences.md` for all browser automation tasks."

## Output

Plain text result shown to user (example):

```
agent-browser: ready
Environment: macOS
Connection method: --auto-connect
Chrome: connected and ready
Open any web URL using the command recorded in dev-swarm/user_preferences.md
```

If the user requested file output, write the same content to the specified path.

## Common Issues

- **pnpm not found**: install pnpm first (`npm install -g pnpm`), then retry
- **Chrome not detected**: ensure Chrome is running with remote debugging enabled
- **cdp ws URL not reachable**: check that the chrome-devtool-proxy binary is running on the host and the firewall allows the connection
- **agent-browser snapshot returns empty**: the page may still be loading — use `agent-browser wait --load networkidle` before snapshot
