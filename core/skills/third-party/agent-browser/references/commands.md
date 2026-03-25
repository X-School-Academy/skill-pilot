# Command Reference

Complete reference for all agent-browser commands. For quick start and common patterns, see SKILL.md.

## Navigation

```bash
core/bin/agent-browser open <url>      # Navigate to URL (aliases: goto, navigate)
                              # Supports: https://, http://, file://, about:, data://
                              # Auto-prepends https:// if no protocol given
core/bin/agent-browser back            # Go back
core/bin/agent-browser forward         # Go forward
core/bin/agent-browser reload          # Reload page
core/bin/agent-browser close           # Close browser (aliases: quit, exit)
core/bin/agent-browser connect 9222    # Connect to browser via CDP port
```

## Snapshot (page analysis)

```bash
core/bin/agent-browser snapshot            # Full accessibility tree
core/bin/agent-browser snapshot -i         # Interactive elements only (recommended)
core/bin/agent-browser snapshot -c         # Compact output
core/bin/agent-browser snapshot -d 3       # Limit depth to 3
core/bin/agent-browser snapshot -s "#main" # Scope to CSS selector
```

## Interactions (use @refs from snapshot)

```bash
core/bin/agent-browser click @e1           # Click
core/bin/agent-browser click @e1 --new-tab # Click and open in new tab
core/bin/agent-browser dblclick @e1        # Double-click
core/bin/agent-browser focus @e1           # Focus element
core/bin/agent-browser fill @e2 "text"     # Clear and type
core/bin/agent-browser type @e2 "text"     # Type without clearing
core/bin/agent-browser press Enter         # Press key (alias: key)
core/bin/agent-browser press Control+a     # Key combination
core/bin/agent-browser keydown Shift       # Hold key down
core/bin/agent-browser keyup Shift         # Release key
core/bin/agent-browser hover @e1           # Hover
core/bin/agent-browser check @e1           # Check checkbox
core/bin/agent-browser uncheck @e1         # Uncheck checkbox
core/bin/agent-browser select @e1 "value"  # Select dropdown option
core/bin/agent-browser select @e1 "a" "b"  # Select multiple options
core/bin/agent-browser scroll down 500     # Scroll page (default: down 300px)
core/bin/agent-browser scrollintoview @e1  # Scroll element into view (alias: scrollinto)
core/bin/agent-browser drag @e1 @e2        # Drag and drop
core/bin/agent-browser upload @e1 file.pdf # Upload files
```

## Get Information

```bash
core/bin/agent-browser get text @e1        # Get element text
core/bin/agent-browser get html @e1        # Get innerHTML
core/bin/agent-browser get value @e1       # Get input value
core/bin/agent-browser get attr @e1 href   # Get attribute
core/bin/agent-browser get title           # Get page title
core/bin/agent-browser get url             # Get current URL
core/bin/agent-browser get cdp-url         # Get CDP WebSocket URL
core/bin/agent-browser get count ".item"   # Count matching elements
core/bin/agent-browser get box @e1         # Get bounding box
core/bin/agent-browser get styles @e1      # Get computed styles (font, color, bg, etc.)
```

## Check State

```bash
core/bin/agent-browser is visible @e1      # Check if visible
core/bin/agent-browser is enabled @e1      # Check if enabled
core/bin/agent-browser is checked @e1      # Check if checked
```

## Screenshots and PDF

```bash
core/bin/agent-browser screenshot          # Save to temporary directory
core/bin/agent-browser screenshot path.png # Save to specific path
core/bin/agent-browser screenshot --full   # Full page
core/bin/agent-browser pdf output.pdf      # Save as PDF
```

## Video Recording

```bash
core/bin/agent-browser record start ./demo.webm    # Start recording
core/bin/agent-browser click @e1                   # Perform actions
core/bin/agent-browser record stop                 # Stop and save video
core/bin/agent-browser record restart ./take2.webm # Stop current + start new
```

## Wait

```bash
core/bin/agent-browser wait @e1                     # Wait for element
core/bin/agent-browser wait 2000                    # Wait milliseconds
core/bin/agent-browser wait --text "Success"        # Wait for text (or -t)
core/bin/agent-browser wait --url "**/dashboard"    # Wait for URL pattern (or -u)
core/bin/agent-browser wait --load networkidle      # Wait for network idle (or -l)
core/bin/agent-browser wait --fn "window.ready"     # Wait for JS condition (or -f)
```

## Mouse Control

```bash
core/bin/agent-browser mouse move 100 200      # Move mouse
core/bin/agent-browser mouse down left         # Press button
core/bin/agent-browser mouse up left           # Release button
core/bin/agent-browser mouse wheel 100         # Scroll wheel
```

## Semantic Locators (alternative to refs)

```bash
core/bin/agent-browser find role button click --name "Submit"
core/bin/agent-browser find text "Sign In" click
core/bin/agent-browser find text "Sign In" click --exact      # Exact match only
core/bin/agent-browser find label "Email" fill "user@test.com"
core/bin/agent-browser find placeholder "Search" type "query"
core/bin/agent-browser find alt "Logo" click
core/bin/agent-browser find title "Close" click
core/bin/agent-browser find testid "submit-btn" click
core/bin/agent-browser find first ".item" click
core/bin/agent-browser find last ".item" click
core/bin/agent-browser find nth 2 "a" hover
```

## Browser Settings

```bash
core/bin/agent-browser set viewport 1920 1080          # Set viewport size
core/bin/agent-browser set viewport 1920 1080 2        # 2x retina (same CSS size, higher res screenshots)
core/bin/agent-browser set device "iPhone 14"          # Emulate device
core/bin/agent-browser set geo 37.7749 -122.4194       # Set geolocation (alias: geolocation)
core/bin/agent-browser set offline on                  # Toggle offline mode
core/bin/agent-browser set headers '{"X-Key":"v"}'     # Extra HTTP headers
core/bin/agent-browser set credentials user pass       # HTTP basic auth (alias: auth)
core/bin/agent-browser set media dark                  # Emulate color scheme
core/bin/agent-browser set media light reduced-motion  # Light mode + reduced motion
```

## Cookies and Storage

```bash
core/bin/agent-browser cookies                     # Get all cookies
core/bin/agent-browser cookies set name value      # Set cookie
core/bin/agent-browser cookies clear               # Clear cookies
core/bin/agent-browser storage local               # Get all localStorage
core/bin/agent-browser storage local key           # Get specific key
core/bin/agent-browser storage local set k v       # Set value
core/bin/agent-browser storage local clear         # Clear all
```

## Network

```bash
core/bin/agent-browser network route <url>              # Intercept requests
core/bin/agent-browser network route <url> --abort      # Block requests
core/bin/agent-browser network route <url> --body '{}'  # Mock response
core/bin/agent-browser network unroute [url]            # Remove routes
core/bin/agent-browser network requests                 # View tracked requests
core/bin/agent-browser network requests --filter api    # Filter requests
```

## Tabs and Windows

```bash
core/bin/agent-browser tab                 # List tabs
core/bin/agent-browser tab new [url]       # New tab
core/bin/agent-browser tab 2               # Switch to tab by index
core/bin/agent-browser tab close           # Close current tab
core/bin/agent-browser tab close 2         # Close tab by index
core/bin/agent-browser window new          # New window
```

## Frames

```bash
core/bin/agent-browser frame "#iframe"     # Switch to iframe by CSS selector
core/bin/agent-browser frame @e3           # Switch to iframe by element ref
core/bin/agent-browser frame main          # Back to main frame
```

### Iframe support

Iframes are detected automatically during snapshots. When the main-frame snapshot runs, `Iframe` nodes are resolved and their content is inlined beneath the iframe element in the output (one level of nesting; iframes within iframes are not expanded).

```bash
core/bin/agent-browser snapshot -i
# @e3 [Iframe] "payment-frame"
#   @e4 [input] "Card number"
#   @e5 [button] "Pay"

# Interact directly — refs inside iframes already work
core/bin/agent-browser fill @e4 "4111111111111111"
core/bin/agent-browser click @e5

# Or switch frame context for scoped snapshots
core/bin/agent-browser frame @e3               # Switch using element ref
core/bin/agent-browser snapshot -i             # Snapshot scoped to that iframe
core/bin/agent-browser frame main              # Return to main frame
```

The `frame` command accepts:
- **Element refs** — `frame @e3` resolves the ref to an iframe element
- **CSS selectors** — `frame "#payment-iframe"` finds the iframe by selector
- **Frame name/URL** — matches against the browser's frame tree

## Dialogs

```bash
core/bin/agent-browser dialog accept [text]  # Accept dialog
core/bin/agent-browser dialog dismiss        # Dismiss dialog
```

## JavaScript

```bash
core/bin/agent-browser eval "document.title"          # Simple expressions only
core/bin/agent-browser eval -b "<base64>"             # Any JavaScript (base64 encoded)
core/bin/agent-browser eval --stdin                   # Read script from stdin
```

Use `-b`/`--base64` or `--stdin` for reliable execution. Shell escaping with nested quotes and special characters is error-prone.

```bash
# Base64 encode your script, then:
core/bin/agent-browser eval -b "ZG9jdW1lbnQucXVlcnlTZWxlY3RvcignW3NyYyo9Il9uZXh0Il0nKQ=="

# Or use stdin with heredoc for multiline scripts:
cat <<'EOF' | core/bin/agent-browser eval --stdin
const links = document.querySelectorAll('a');
Array.from(links).map(a => a.href);
EOF
```

## State Management

```bash
core/bin/agent-browser state save auth.json    # Save cookies, storage, auth state
core/bin/agent-browser state load auth.json    # Restore saved state
```

## Global Options

```bash
core/bin/agent-browser --session <name> ...    # Isolated browser session
core/bin/agent-browser --json ...              # JSON output for parsing
core/bin/agent-browser --headed ...            # Show browser window (not headless)
core/bin/agent-browser --full ...              # Full page screenshot (-f)
core/bin/agent-browser --cdp <port> ...        # Connect via Chrome DevTools Protocol
core/bin/agent-browser -p <provider> ...       # Cloud browser provider (--provider)
core/bin/agent-browser --proxy <url> ...       # Use proxy server
core/bin/agent-browser --proxy-bypass <hosts>  # Hosts to bypass proxy
core/bin/agent-browser --headers <json> ...    # HTTP headers scoped to URL's origin
core/bin/agent-browser --executable-path <p>   # Custom browser executable
core/bin/agent-browser --extension <path> ...  # Load browser extension (repeatable)
core/bin/agent-browser --ignore-https-errors   # Ignore SSL certificate errors
core/bin/agent-browser --help                  # Show help (-h)
core/bin/agent-browser --version               # Show version (-V)
core/bin/agent-browser <command> --help        # Show detailed help for a command
```

## Debugging

```bash
core/bin/agent-browser --headed open example.com   # Show browser window
core/bin/agent-browser --cdp 9222 snapshot         # Connect via CDP port
core/bin/agent-browser connect 9222                # Alternative: connect command
core/bin/agent-browser console                     # View console messages
core/bin/agent-browser console --clear             # Clear console
core/bin/agent-browser errors                      # View page errors
core/bin/agent-browser errors --clear              # Clear errors
core/bin/agent-browser highlight @e1               # Highlight element
core/bin/agent-browser inspect                     # Open Chrome DevTools for this session
core/bin/agent-browser trace start                 # Start recording trace
core/bin/agent-browser trace stop trace.zip        # Stop and save trace
core/bin/agent-browser profiler start              # Start Chrome DevTools profiling
core/bin/agent-browser profiler stop trace.json    # Stop and save profile
```

## Environment Variables

```bash
AGENT_BROWSER_SESSION="mysession"            # Default session name
AGENT_BROWSER_EXECUTABLE_PATH="/path/chrome" # Custom browser path
AGENT_BROWSER_EXTENSIONS="/ext1,/ext2"       # Comma-separated extension paths
AGENT_BROWSER_PROVIDER="browserbase"         # Cloud browser provider
AGENT_BROWSER_STREAM_PORT="9223"             # WebSocket streaming port
AGENT_BROWSER_HOME="/path/to/agent-browser"  # Custom install location
```
