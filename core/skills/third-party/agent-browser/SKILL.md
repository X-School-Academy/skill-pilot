---
name: agent-browser
description: Web browser automation CLI for AI agents. Use when the user needs to interact with websites, including navigating pages, filling forms, clicking buttons, taking screenshots, extracting data, testing web apps, or automating any browser task. Triggers include requests to "open a website", "fill out a form", "click a button", "take a screenshot", "scrape data from a page", "test this web app", "login to a site", "automate browser actions", or any task requiring programmatic web interaction.
allowed-tools: Bash(core/bin/agent-browser:*)
---

# Browser Automation with agent-browser

The CLI uses Chrome/Chromium via CDP directly through the local wrapper script. Use `core/bin/agent-browser` for all commands in this skill.

## Core Workflow

Every browser automation follows this pattern:

1. **Navigate**: `core/bin/agent-browser open <url>`
2. **Snapshot**: `core/bin/agent-browser snapshot -i` (get element refs like `@e1`, `@e2`)
3. **Interact**: Use refs to click, fill, select
4. **Re-snapshot**: After navigation or DOM changes, get fresh refs

```bash
core/bin/agent-browser open https://example.com/form
core/bin/agent-browser snapshot -i
# Output: @e1 [input type="email"], @e2 [input type="password"], @e3 [button] "Submit"

core/bin/agent-browser fill @e1 "user@example.com"
core/bin/agent-browser fill @e2 "password123"
core/bin/agent-browser click @e3
core/bin/agent-browser wait --load networkidle
core/bin/agent-browser snapshot -i  # Check result
```

## Command Chaining

Commands can be chained with `&&` in a single shell invocation. The browser persists between commands via a background daemon, so chaining is safe and more efficient than separate calls.

```bash
# Chain open + wait + snapshot in one call
core/bin/agent-browser open https://example.com && core/bin/agent-browser wait --load networkidle && core/bin/agent-browser snapshot -i

# Chain multiple interactions
core/bin/agent-browser fill @e1 "user@example.com" && core/bin/agent-browser fill @e2 "password123" && core/bin/agent-browser click @e3

# Navigate and capture
core/bin/agent-browser open https://example.com && core/bin/agent-browser wait --load networkidle && core/bin/agent-browser screenshot page.png
```

**When to chain:** Use `&&` when you don't need to read the output of an intermediate command before proceeding (e.g., open + wait + screenshot). Run commands separately when you need to parse the output first (e.g., snapshot to discover refs, then interact using those refs).

## Handling Authentication

When automating a site that requires login, choose the approach that fits:

**Option 1: Import auth from the user's browser (fastest for one-off tasks)**

```bash
# Connect to the user's running Chrome (they're already logged in)
core/bin/agent-browser --auto-connect state save ./auth.json
# Use that auth state
core/bin/agent-browser --state ./auth.json open https://app.example.com/dashboard
```

State files contain session tokens in plaintext -- add to `.gitignore` and delete when no longer needed. Set `AGENT_BROWSER_ENCRYPTION_KEY` for encryption at rest.

**Option 2: Persistent profile (simplest for recurring tasks)**

```bash
# First run: login manually or via automation
core/bin/agent-browser --profile ~/.myapp open https://app.example.com/login
# ... fill credentials, submit ...

# All future runs: already authenticated
core/bin/agent-browser --profile ~/.myapp open https://app.example.com/dashboard
```

**Option 3: Session name (auto-save/restore cookies + localStorage)**

```bash
core/bin/agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
core/bin/agent-browser close  # State auto-saved

# Next time: state auto-restored
core/bin/agent-browser --session-name myapp open https://app.example.com/dashboard
```

**Option 4: Auth vault (credentials stored encrypted, login by name)**

```bash
echo "$PASSWORD" | core/bin/agent-browser auth save myapp --url https://app.example.com/login --username user --password-stdin
core/bin/agent-browser auth login myapp
```

`auth login` navigates with `load` and then waits for login form selectors to appear before filling/clicking, which is more reliable on delayed SPA login screens.

**Option 5: State file (manual save/load)**

```bash
# After logging in:
core/bin/agent-browser state save ./auth.json
# In a future session:
core/bin/agent-browser state load ./auth.json
core/bin/agent-browser open https://app.example.com/dashboard
```

See [references/authentication.md](references/authentication.md) for OAuth, 2FA, cookie-based auth, and token refresh patterns.

## Essential Commands

```bash
# Navigation
core/bin/agent-browser open <url>              # Navigate (aliases: goto, navigate)
core/bin/agent-browser close                   # Close browser

# Snapshot
core/bin/agent-browser snapshot -i             # Interactive elements with refs (recommended)
core/bin/agent-browser snapshot -i -C          # Include cursor-interactive elements (divs with onclick, cursor:pointer)
core/bin/agent-browser snapshot -s "#selector" # Scope to CSS selector

# Interaction (use @refs from snapshot)
core/bin/agent-browser click @e1               # Click element
core/bin/agent-browser click @e1 --new-tab     # Click and open in new tab
core/bin/agent-browser fill @e2 "text"         # Clear and type text
core/bin/agent-browser type @e2 "text"         # Type without clearing
core/bin/agent-browser select @e1 "option"     # Select dropdown option
core/bin/agent-browser check @e1               # Check checkbox
core/bin/agent-browser press Enter             # Press key
core/bin/agent-browser keyboard type "text"    # Type at current focus (no selector)
core/bin/agent-browser keyboard inserttext "text"  # Insert without key events
core/bin/agent-browser scroll down 500         # Scroll page
core/bin/agent-browser scroll down 500 --selector "div.content"  # Scroll within a specific container

# Get information
core/bin/agent-browser get text @e1            # Get element text
core/bin/agent-browser get url                 # Get current URL
core/bin/agent-browser get title               # Get page title
core/bin/agent-browser get cdp-url             # Get CDP WebSocket URL

# Wait
core/bin/agent-browser wait @e1                # Wait for element
core/bin/agent-browser wait --load networkidle # Wait for network idle
core/bin/agent-browser wait --url "**/page"    # Wait for URL pattern
core/bin/agent-browser wait 2000               # Wait milliseconds
core/bin/agent-browser wait --text "Welcome"    # Wait for text to appear (substring match)
core/bin/agent-browser wait --fn "!document.body.innerText.includes('Loading...')"  # Wait for text to disappear
core/bin/agent-browser wait "#spinner" --state hidden  # Wait for element to disappear

# Downloads
core/bin/agent-browser download @e1 ./file.pdf          # Click element to trigger download
core/bin/agent-browser wait --download ./output.zip     # Wait for any download to complete
core/bin/agent-browser --download-path ./downloads open <url>  # Set default download directory

# Network
core/bin/agent-browser network requests                 # Inspect tracked requests
core/bin/agent-browser network route "**/api/*" --abort  # Block matching requests
core/bin/agent-browser network har start                # Start HAR recording
core/bin/agent-browser network har stop ./capture.har   # Stop and save HAR file

# Viewport & Device Emulation
core/bin/agent-browser set viewport 1920 1080          # Set viewport size (default: 1280x720)
core/bin/agent-browser set viewport 1920 1080 2        # 2x retina (same CSS size, higher res screenshots)
core/bin/agent-browser set device "iPhone 14"          # Emulate device (viewport + user agent)

# Capture
core/bin/agent-browser screenshot              # Screenshot to temp dir
core/bin/agent-browser screenshot --full       # Full page screenshot
core/bin/agent-browser screenshot --annotate   # Annotated screenshot with numbered element labels
core/bin/agent-browser screenshot --screenshot-dir ./shots  # Save to custom directory
core/bin/agent-browser screenshot --screenshot-format jpeg --screenshot-quality 80
core/bin/agent-browser pdf output.pdf          # Save as PDF

# Clipboard
core/bin/agent-browser clipboard read                      # Read text from clipboard
core/bin/agent-browser clipboard write "Hello, World!"     # Write text to clipboard
core/bin/agent-browser clipboard copy                      # Copy current selection
core/bin/agent-browser clipboard paste                     # Paste from clipboard

# Diff (compare page states)
core/bin/agent-browser diff snapshot                          # Compare current vs last snapshot
core/bin/agent-browser diff snapshot --baseline before.txt    # Compare current vs saved file
core/bin/agent-browser diff screenshot --baseline before.png  # Visual pixel diff
core/bin/agent-browser diff url <url1> <url2>                 # Compare two pages
core/bin/agent-browser diff url <url1> <url2> --wait-until networkidle  # Custom wait strategy
core/bin/agent-browser diff url <url1> <url2> --selector "#main"  # Scope to element
```

## Batch Execution

Execute multiple commands in a single invocation by piping a JSON array of string arrays to `batch`. This avoids per-command process startup overhead when running multi-step workflows.

```bash
echo '[
  ["open", "https://example.com"],
  ["snapshot", "-i"],
  ["click", "@e1"],
  ["screenshot", "result.png"]
]' | core/bin/agent-browser batch --json

# Stop on first error
core/bin/agent-browser batch --bail < commands.json
```

Use `batch` when you have a known sequence of commands that don't depend on intermediate output. Use separate commands or `&&` chaining when you need to parse output between steps (e.g., snapshot to discover refs, then interact).

## Common Patterns

### Form Submission

```bash
core/bin/agent-browser open https://example.com/signup
core/bin/agent-browser snapshot -i
core/bin/agent-browser fill @e1 "Jane Doe"
core/bin/agent-browser fill @e2 "jane@example.com"
core/bin/agent-browser select @e3 "California"
core/bin/agent-browser check @e4
core/bin/agent-browser click @e5
core/bin/agent-browser wait --load networkidle
```

### Authentication with Auth Vault (Recommended)

```bash
# Save credentials once (encrypted with AGENT_BROWSER_ENCRYPTION_KEY)
# Recommended: pipe password via stdin to avoid shell history exposure
echo "pass" | core/bin/agent-browser auth save github --url https://github.com/login --username user --password-stdin

# Login using saved profile (LLM never sees password)
core/bin/agent-browser auth login github

# List/show/delete profiles
core/bin/agent-browser auth list
core/bin/agent-browser auth show github
core/bin/agent-browser auth delete github
```

`auth login` waits for username/password/submit selectors before interacting, with a timeout tied to the default action timeout.

### Authentication with State Persistence

```bash
# Login once and save state
core/bin/agent-browser open https://app.example.com/login
core/bin/agent-browser snapshot -i
core/bin/agent-browser fill @e1 "$USERNAME"
core/bin/agent-browser fill @e2 "$PASSWORD"
core/bin/agent-browser click @e3
core/bin/agent-browser wait --url "**/dashboard"
core/bin/agent-browser state save auth.json

# Reuse in future sessions
core/bin/agent-browser state load auth.json
core/bin/agent-browser open https://app.example.com/dashboard
```

### Session Persistence

```bash
# Auto-save/restore cookies and localStorage across browser restarts
core/bin/agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
core/bin/agent-browser close  # State auto-saved to ~/.agent-browser/sessions/

# Next time, state is auto-loaded
core/bin/agent-browser --session-name myapp open https://app.example.com/dashboard

# Encrypt state at rest
export AGENT_BROWSER_ENCRYPTION_KEY=$(openssl rand -hex 32)
core/bin/agent-browser --session-name secure open https://app.example.com

# Manage saved states
core/bin/agent-browser state list
core/bin/agent-browser state show myapp-default.json
core/bin/agent-browser state clear myapp
core/bin/agent-browser state clean --older-than 7
```

### Working with Iframes

Iframe content is automatically inlined in snapshots. Refs inside iframes carry frame context, so you can interact with them directly.

```bash
core/bin/agent-browser open https://example.com/checkout
core/bin/agent-browser snapshot -i
# @e1 [heading] "Checkout"
# @e2 [Iframe] "payment-frame"
#   @e3 [input] "Card number"
#   @e4 [input] "Expiry"
#   @e5 [button] "Pay"

# Interact directly — no frame switch needed
core/bin/agent-browser fill @e3 "4111111111111111"
core/bin/agent-browser fill @e4 "12/28"
core/bin/agent-browser click @e5

# To scope a snapshot to one iframe:
core/bin/agent-browser frame @e2
core/bin/agent-browser snapshot -i         # Only iframe content
core/bin/agent-browser frame main          # Return to main frame
```

### Data Extraction

```bash
core/bin/agent-browser open https://example.com/products
core/bin/agent-browser snapshot -i
core/bin/agent-browser get text @e5           # Get specific element text
core/bin/agent-browser get text body > page.txt  # Get all page text

# JSON output for parsing
core/bin/agent-browser snapshot -i --json
core/bin/agent-browser get text @e1 --json
```

### Parallel Sessions

```bash
core/bin/agent-browser --session site1 open https://site-a.com
core/bin/agent-browser --session site2 open https://site-b.com

core/bin/agent-browser --session site1 snapshot -i
core/bin/agent-browser --session site2 snapshot -i

core/bin/agent-browser session list
```

### Connect to Existing Chrome

```bash
# Auto-discover running Chrome with remote debugging enabled
core/bin/agent-browser --auto-connect open https://example.com
core/bin/agent-browser --auto-connect snapshot

# Or with explicit CDP port
core/bin/agent-browser --cdp 9222 snapshot
```

Auto-connect discovers Chrome via `DevToolsActivePort`, common debugging ports (9222, 9229), and falls back to a direct WebSocket connection if HTTP-based CDP discovery fails.

### Color Scheme (Dark Mode)

```bash
# Persistent dark mode via flag (applies to all pages and new tabs)
core/bin/agent-browser --color-scheme dark open https://example.com

# Or via environment variable
AGENT_BROWSER_COLOR_SCHEME=dark core/bin/agent-browser open https://example.com

# Or set during session (persists for subsequent commands)
core/bin/agent-browser set media dark
```

### Viewport & Responsive Testing

```bash
# Set a custom viewport size (default is 1280x720)
core/bin/agent-browser set viewport 1920 1080
core/bin/agent-browser screenshot desktop.png

# Test mobile-width layout
core/bin/agent-browser set viewport 375 812
core/bin/agent-browser screenshot mobile.png

# Retina/HiDPI: same CSS layout at 2x pixel density
# Screenshots stay at logical viewport size, but content renders at higher DPI
core/bin/agent-browser set viewport 1920 1080 2
core/bin/agent-browser screenshot retina.png

# Device emulation (sets viewport + user agent in one step)
core/bin/agent-browser set device "iPhone 14"
core/bin/agent-browser screenshot device.png
```

The `scale` parameter (3rd argument) sets `window.devicePixelRatio` without changing CSS layout. Use it when testing retina rendering or capturing higher-resolution screenshots.

### Visual Browser (Debugging)

```bash
core/bin/agent-browser --headed open https://example.com
core/bin/agent-browser highlight @e1          # Highlight element
core/bin/agent-browser inspect                # Open Chrome DevTools for the active page
core/bin/agent-browser record start demo.webm # Record session
core/bin/agent-browser profiler start         # Start Chrome DevTools profiling
core/bin/agent-browser profiler stop trace.json # Stop and save profile (path optional)
```

Use `AGENT_BROWSER_HEADED=1` to enable headed mode via environment variable. Browser extensions work in both headed and headless mode.

### Local Files (PDFs, HTML)

```bash
# Open local files with file:// URLs
core/bin/agent-browser --allow-file-access open file:///path/to/document.pdf
core/bin/agent-browser --allow-file-access open file:///path/to/page.html
core/bin/agent-browser screenshot output.png
```

### iOS Simulator (Mobile Safari)

```bash
# List available iOS simulators
core/bin/agent-browser device list

# Launch Safari on a specific device
core/bin/agent-browser -p ios --device "iPhone 16 Pro" open https://example.com

# Same workflow as desktop - snapshot, interact, re-snapshot
core/bin/agent-browser -p ios snapshot -i
core/bin/agent-browser -p ios tap @e1          # Tap (alias for click)
core/bin/agent-browser -p ios fill @e2 "text"
core/bin/agent-browser -p ios swipe up         # Mobile-specific gesture

# Take screenshot
core/bin/agent-browser -p ios screenshot mobile.png

# Close session (shuts down simulator)
core/bin/agent-browser -p ios close
```

**Requirements:** macOS with Xcode, Appium (`npm install -g appium && appium driver install xcuitest`)

**Real devices:** Works with physical iOS devices if pre-configured. Use `--device "<UDID>"` where UDID is from `xcrun xctrace list devices`.

## Security

All security features are opt-in. By default, agent-browser imposes no restrictions on navigation, actions, or output.

### Content Boundaries (Recommended for AI Agents)

Enable `--content-boundaries` to wrap page-sourced output in markers that help LLMs distinguish tool output from untrusted page content:

```bash
export AGENT_BROWSER_CONTENT_BOUNDARIES=1
core/bin/agent-browser snapshot
# Output:
# --- AGENT_BROWSER_PAGE_CONTENT nonce=<hex> origin=https://example.com ---
# [accessibility tree]
# --- END_AGENT_BROWSER_PAGE_CONTENT nonce=<hex> ---
```

### Domain Allowlist

Restrict navigation to trusted domains. Wildcards like `*.example.com` also match the bare domain `example.com`. Sub-resource requests, WebSocket, and EventSource connections to non-allowed domains are also blocked. Include CDN domains your target pages depend on:

```bash
export AGENT_BROWSER_ALLOWED_DOMAINS="example.com,*.example.com"
core/bin/agent-browser open https://example.com        # OK
core/bin/agent-browser open https://malicious.com       # Blocked
```

### Action Policy

Use a policy file to gate destructive actions:

```bash
export AGENT_BROWSER_ACTION_POLICY=./policy.json
```

Example `policy.json`:

```json
{ "default": "deny", "allow": ["navigate", "snapshot", "click", "scroll", "wait", "get"] }
```

Auth vault operations (`auth login`, etc.) bypass action policy but domain allowlist still applies.

### Output Limits

Prevent context flooding from large pages:

```bash
export AGENT_BROWSER_MAX_OUTPUT=50000
```

## Diffing (Verifying Changes)

Use `diff snapshot` after performing an action to verify it had the intended effect. This compares the current accessibility tree against the last snapshot taken in the session.

```bash
# Typical workflow: snapshot -> action -> diff
core/bin/agent-browser snapshot -i          # Take baseline snapshot
core/bin/agent-browser click @e2            # Perform action
core/bin/agent-browser diff snapshot        # See what changed (auto-compares to last snapshot)
```

For visual regression testing or monitoring:

```bash
# Save a baseline screenshot, then compare later
core/bin/agent-browser screenshot baseline.png
# ... time passes or changes are made ...
core/bin/agent-browser diff screenshot --baseline baseline.png

# Compare staging vs production
core/bin/agent-browser diff url https://staging.example.com https://prod.example.com --screenshot
```

`diff snapshot` output uses `+` for additions and `-` for removals, similar to git diff. `diff screenshot` produces a diff image with changed pixels highlighted in red, plus a mismatch percentage.

## Timeouts and Slow Pages

The default timeout is 25 seconds. This can be overridden with the `AGENT_BROWSER_DEFAULT_TIMEOUT` environment variable (value in milliseconds). For slow websites or large pages, use explicit waits instead of relying on the default timeout:

```bash
# Wait for network activity to settle (best for slow pages)
core/bin/agent-browser wait --load networkidle

# Wait for a specific element to appear
core/bin/agent-browser wait "#content"
core/bin/agent-browser wait @e1

# Wait for a specific URL pattern (useful after redirects)
core/bin/agent-browser wait --url "**/dashboard"

# Wait for a JavaScript condition
core/bin/agent-browser wait --fn "document.readyState === 'complete'"

# Wait a fixed duration (milliseconds) as a last resort
core/bin/agent-browser wait 5000
```

When dealing with consistently slow websites, use `wait --load networkidle` after `open` to ensure the page is fully loaded before taking a snapshot. If a specific element is slow to render, wait for it directly with `wait <selector>` or `wait @ref`.

## Session Management and Cleanup

When running multiple agents or automations concurrently, always use named sessions to avoid conflicts:

```bash
# Each agent gets its own isolated session
core/bin/agent-browser --session agent1 open site-a.com
core/bin/agent-browser --session agent2 open site-b.com

# Check active sessions
core/bin/agent-browser session list
```

Always close your browser session when done to avoid leaked processes:

```bash
core/bin/agent-browser close                    # Close default session
core/bin/agent-browser --session agent1 close   # Close specific session
```

If a previous session was not closed properly, the daemon may still be running. Use `core/bin/agent-browser close` to clean it up before starting new work.

To auto-shutdown the daemon after a period of inactivity (useful for ephemeral/CI environments):

```bash
AGENT_BROWSER_IDLE_TIMEOUT_MS=60000 agent-browser open example.com
```

## Ref Lifecycle (Important)

Refs (`@e1`, `@e2`, etc.) are invalidated when the page changes. Always re-snapshot after:

- Clicking links or buttons that navigate
- Form submissions
- Dynamic content loading (dropdowns, modals)

```bash
core/bin/agent-browser click @e5              # Navigates to new page
core/bin/agent-browser snapshot -i            # MUST re-snapshot
core/bin/agent-browser click @e1              # Use new refs
```

## Annotated Screenshots (Vision Mode)

Use `--annotate` to take a screenshot with numbered labels overlaid on interactive elements. Each label `[N]` maps to ref `@eN`. This also caches refs, so you can interact with elements immediately without a separate snapshot.

```bash
core/bin/agent-browser screenshot --annotate
# Output includes the image path and a legend:
#   [1] @e1 button "Submit"
#   [2] @e2 link "Home"
#   [3] @e3 textbox "Email"
core/bin/agent-browser click @e2              # Click using ref from annotated screenshot
```

Use annotated screenshots when:

- The page has unlabeled icon buttons or visual-only elements
- You need to verify visual layout or styling
- Canvas or chart elements are present (invisible to text snapshots)
- You need spatial reasoning about element positions

## Semantic Locators (Alternative to Refs)

When refs are unavailable or unreliable, use semantic locators:

```bash
core/bin/agent-browser find text "Sign In" click
core/bin/agent-browser find label "Email" fill "user@test.com"
core/bin/agent-browser find role button click --name "Submit"
core/bin/agent-browser find placeholder "Search" type "query"
core/bin/agent-browser find testid "submit-btn" click
```

## JavaScript Evaluation (eval)

Use `eval` to run JavaScript in the browser context. **Shell quoting can corrupt complex expressions** -- use `--stdin` or `-b` to avoid issues.

```bash
# Simple expressions work with regular quoting
core/bin/agent-browser eval 'document.title'
core/bin/agent-browser eval 'document.querySelectorAll("img").length'

# Complex JS: use --stdin with heredoc (RECOMMENDED)
core/bin/agent-browser eval --stdin <<'EVALEOF'
JSON.stringify(
  Array.from(document.querySelectorAll("img"))
    .filter(i => !i.alt)
    .map(i => ({ src: i.src.split("/").pop(), width: i.width }))
)
EVALEOF

# Alternative: base64 encoding (avoids all shell escaping issues)
core/bin/agent-browser eval -b "$(echo -n 'Array.from(document.querySelectorAll("a")).map(a => a.href)' | base64)"
```

**Why this matters:** When the shell processes your command, inner double quotes, `!` characters (history expansion), backticks, and `$()` can all corrupt the JavaScript before it reaches agent-browser. The `--stdin` and `-b` flags bypass shell interpretation entirely.

**Rules of thumb:**

- Single-line, no nested quotes -> regular `eval 'expression'` with single quotes is fine
- Nested quotes, arrow functions, template literals, or multiline -> use `eval --stdin <<'EVALEOF'`
- Programmatic/generated scripts -> use `eval -b` with base64

## Configuration File

Create `core/bin/agent-browser.json` in the project root for persistent settings:

```json
{
  "headed": true,
  "proxy": "http://localhost:8080",
  "profile": "./browser-data"
}
```

Priority (lowest to highest): `~/.agent-browser/config.json` < `./agent-browser.json` < env vars < CLI flags. Use `--config <path>` or `AGENT_BROWSER_CONFIG` env var for a custom config file (exits with error if missing/invalid). All CLI options map to camelCase keys (e.g., `--executable-path` -> `"executablePath"`). Boolean flags accept `true`/`false` values (e.g., `--headed false` overrides config). Extensions from user and project configs are merged, not replaced.

## Deep-Dive Documentation

| Reference                                                            | When to Use                                               |
| -------------------------------------------------------------------- | --------------------------------------------------------- |
| [references/commands.md](references/commands.md)                     | Full command reference with all options                   |
| [references/snapshot-refs.md](references/snapshot-refs.md)           | Ref lifecycle, invalidation rules, troubleshooting        |
| [references/session-management.md](references/session-management.md) | Parallel sessions, state persistence, concurrent scraping |
| [references/authentication.md](references/authentication.md)         | Login flows, OAuth, 2FA handling, state reuse             |
| [references/video-recording.md](references/video-recording.md)       | Recording workflows for debugging and documentation       |
| [references/profiling.md](references/profiling.md)                   | Chrome DevTools profiling for performance analysis        |
| [references/proxy-support.md](references/proxy-support.md)           | Proxy configuration, geo-testing, rotating proxies        |

## Browser Engine Selection

Use `--engine` to choose a local browser engine. The default is `chrome`.

```bash
# Use Lightpanda (fast headless browser, requires separate install)
core/bin/agent-browser --engine lightpanda open example.com

# Via environment variable
export AGENT_BROWSER_ENGINE=lightpanda
core/bin/agent-browser open example.com

# With custom binary path
core/bin/agent-browser --engine lightpanda --executable-path /path/to/lightpanda open example.com
```

Supported engines:
- `chrome` (default) -- Chrome/Chromium via CDP
- `lightpanda` -- Lightpanda headless browser via CDP (10x faster, 10x less memory than Chrome)

Lightpanda does not support `--extension`, `--profile`, `--state`, or `--allow-file-access`. Install Lightpanda from https://lightpanda.io/docs/open-source/installation.

## Ready-to-Use Templates

| Template                                                                 | Description                         |
| ------------------------------------------------------------------------ | ----------------------------------- |
| [templates/form-automation.sh](templates/form-automation.sh)             | Form filling with validation        |
| [templates/authenticated-session.sh](templates/authenticated-session.sh) | Login once, reuse state             |
| [templates/capture-workflow.sh](templates/capture-workflow.sh)           | Content extraction with screenshots |

```bash
./templates/form-automation.sh https://example.com/form
./templates/authenticated-session.sh https://app.example.com/login
./templates/capture-workflow.sh https://example.com ./output
```
