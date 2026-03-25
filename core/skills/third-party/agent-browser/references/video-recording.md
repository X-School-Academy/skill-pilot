# Video Recording

Capture browser automation as video for debugging, documentation, or verification.

**Related**: [commands.md](commands.md) for full command reference, [SKILL.md](../SKILL.md) for quick start.

## Contents

- [Basic Recording](#basic-recording)
- [Recording Commands](#recording-commands)
- [Use Cases](#use-cases)
- [Best Practices](#best-practices)
- [Output Format](#output-format)
- [Limitations](#limitations)

## Basic Recording

```bash
# Start recording
core/bin/agent-browser record start ./demo.webm

# Perform actions
core/bin/agent-browser open https://example.com
core/bin/agent-browser snapshot -i
core/bin/agent-browser click @e1
core/bin/agent-browser fill @e2 "test input"

# Stop and save
core/bin/agent-browser record stop
```

## Recording Commands

```bash
# Start recording to file
core/bin/agent-browser record start ./output.webm

# Stop current recording
core/bin/agent-browser record stop

# Restart with new file (stops current + starts new)
core/bin/agent-browser record restart ./take2.webm
```

## Use Cases

### Debugging Failed Automation

```bash
#!/bin/bash
# Record automation for debugging

core/bin/agent-browser record start ./debug-$(date +%Y%m%d-%H%M%S).webm

# Run your automation
core/bin/agent-browser open https://app.example.com
core/bin/agent-browser snapshot -i
core/bin/agent-browser click @e1 || {
    echo "Click failed - check recording"
    core/bin/agent-browser record stop
    exit 1
}

core/bin/agent-browser record stop
```

### Documentation Generation

```bash
#!/bin/bash
# Record workflow for documentation

core/bin/agent-browser record start ./docs/how-to-login.webm

core/bin/agent-browser open https://app.example.com/login
core/bin/agent-browser wait 1000  # Pause for visibility

core/bin/agent-browser snapshot -i
core/bin/agent-browser fill @e1 "demo@example.com"
core/bin/agent-browser wait 500

core/bin/agent-browser fill @e2 "password"
core/bin/agent-browser wait 500

core/bin/agent-browser click @e3
core/bin/agent-browser wait --load networkidle
core/bin/agent-browser wait 1000  # Show result

core/bin/agent-browser record stop
```

### CI/CD Test Evidence

```bash
#!/bin/bash
# Record E2E test runs for CI artifacts

TEST_NAME="${1:-e2e-test}"
RECORDING_DIR="./test-recordings"
mkdir -p "$RECORDING_DIR"

core/bin/agent-browser record start "$RECORDING_DIR/$TEST_NAME-$(date +%s).webm"

# Run test
if run_e2e_test; then
    echo "Test passed"
else
    echo "Test failed - recording saved"
fi

core/bin/agent-browser record stop
```

## Best Practices

### 1. Add Pauses for Clarity

```bash
# Slow down for human viewing
core/bin/agent-browser click @e1
core/bin/agent-browser wait 500  # Let viewer see result
```

### 2. Use Descriptive Filenames

```bash
# Include context in filename
core/bin/agent-browser record start ./recordings/login-flow-2024-01-15.webm
core/bin/agent-browser record start ./recordings/checkout-test-run-42.webm
```

### 3. Handle Recording in Error Cases

```bash
#!/bin/bash
set -e

cleanup() {
    core/bin/agent-browser record stop 2>/dev/null || true
    core/bin/agent-browser close 2>/dev/null || true
}
trap cleanup EXIT

core/bin/agent-browser record start ./automation.webm
# ... automation steps ...
```

### 4. Combine with Screenshots

```bash
# Record video AND capture key frames
core/bin/agent-browser record start ./flow.webm

core/bin/agent-browser open https://example.com
core/bin/agent-browser screenshot ./screenshots/step1-homepage.png

core/bin/agent-browser click @e1
core/bin/agent-browser screenshot ./screenshots/step2-after-click.png

core/bin/agent-browser record stop
```

## Output Format

- Default format: WebM (VP8/VP9 codec)
- Compatible with all modern browsers and video players
- Compressed but high quality

## Limitations

- Recording adds slight overhead to automation
- Large recordings can consume significant disk space
- Some headless environments may have codec limitations
