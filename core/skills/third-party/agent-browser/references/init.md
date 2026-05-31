# Init Action

Initialize and verify `core/bin/agent-browser` with the correct Chrome connection method for the current environment before browser automation is attempted.

## When to Use

- The user asks to initialize, set up, or verify agent-browser.
- Browser automation is needed and `core/bin/agent-browser` may not be ready.
- Chrome may be missing or the connection method is unknown.
- A workflow node needs to confirm browser automation readiness before downstream browser tasks.

## Workflow Usage Requirement

When this action is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output: what was checked, what is ready, and any blocking issue.

## Steps

### Step 1: Check CLI Readiness

Run:

```bash
core/bin/agent-browser --version
```

If this fails, report the blocker and do not continue to browser actions.

### Step 2: Detect Environment

Check in this order:

1. Windows WSL: run `uname -r` and check if output contains `microsoft` or `WSL`.
2. macOS: run `uname` and check if output is `Darwin`.
3. Linux with GUI: check if `DISPLAY` or `WAYLAND_DISPLAY` is set.
4. Docker or Linux without GUI: no display is available.

Use the matching platform reference:

- Windows WSL: [init-windows-wsl.md](init-windows-wsl.md)
- macOS: [init-macos.md](init-macos.md)
- Linux with GUI: [init-linux-gui.md](init-linux-gui.md)
- Docker or Linux without GUI: [init-linux-no-gui.md](init-linux-no-gui.md)

### Step 3: Record the Browser Automation Command

After choosing the connection method, update `dev-swarm/user_preferences.md` with the browser automation command.

For macOS or Linux with GUI:

```text
Browser automation command: core/bin/agent-browser --auto-connect open URL
```

For Windows WSL, Docker, or Linux without GUI:

```text
Browser automation command: core/bin/agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
```

### Step 4: Test Browser Connection

Open Google with the recorded connection command:

```bash
core/bin/agent-browser --auto-connect open https://www.google.com
```

or:

```bash
core/bin/agent-browser open https://www.google.com --cdp ws://<host-ip>:9223/devtools/browser/
```

Then run:

```bash
core/bin/agent-browser snapshot -i
```

If the snapshot succeeds, browser automation is ready.

### Step 5: Handle Errors

If the test fails, Chrome may not have remote debugging enabled. Ask the user to enable remote debugging with the platform-appropriate command:

Do not use `--remote-debugging-port` for setup or troubleshooting. Use the platform commands below and the `core/bin/agent-browser` connection options documented in this skill.

Linux:

```bash
google-chrome chrome://inspect/#remote-debugging
```

macOS:

```bash
open -a "Google Chrome" chrome://inspect/#remote-debugging
```

Windows:

```bash
start chrome chrome://inspect/#remote-debugging
```

For other known failures, use [troubleshooting.md](troubleshooting.md).

### Step 6: Report Result

Output plain text. Example:

```text
core/bin/agent-browser: ready
Environment: macOS
Connection method: --auto-connect
Chrome: connected and ready
Open web URLs using the command recorded in dev-swarm/user_preferences.md
```

If the user requested file output, write the same content to the specified path.
