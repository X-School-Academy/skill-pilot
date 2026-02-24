# Claude Code - Headless Mode Reference

Claude Code provides headless execution via the `--print` flag, which outputs the response and exits without entering interactive mode.

## Core Headless Command

```bash
claude --print --dangerously-skip-permissions "your prompt here"
```

## Essential Flags

| Flag | Description |
|------|-------------|
| `-p, --print` | Print response and exit (required for headless) |
| `--dangerously-skip-permissions` | Bypass all permission checks (required for full automation) |
| `--allow-dangerously-skip-permissions` | Enable permission bypass as an option without defaulting to it |

## Optional Configuration Flags

### Model Selection

```bash
--model <model>     # Model alias: 'sonnet', 'opus', or full model ID
--fallback-model <model>  # Fallback when default is overloaded (--print only)
```

### Output Format

```bash
--output-format <format>   # text (default), json, or stream-json
--include-partial-messages # Include partial chunks (with stream-json)
```

### Input Format

```bash
--input-format <format>    # text (default) or stream-json
```

### Session Management

```bash
-c, --continue             # Continue most recent conversation
-r, --resume [session-id]  # Resume specific session
--no-session-persistence   # Don't save sessions (--print only)
--session-id <uuid>        # Use specific session ID
```

### Tool Control

```bash
--allowedTools <tools...>      # Allow specific tools (e.g., "Bash(git:*) Edit")
--disallowedTools <tools...>   # Deny specific tools
--tools <tools...>             # Specify available tools ("", "default", or tool names)
```

### Working Directory

```bash
--add-dir <directories...>     # Additional directories for tool access
```

### System Prompt

```bash
--system-prompt <prompt>       # Override system prompt
--append-system-prompt <prompt> # Append to default system prompt
```

### Budget Control

```bash
--max-budget-usd <amount>      # Maximum API spend (--print only)
```

### JSON Schema Output

```bash
--json-schema <schema>         # JSON Schema for structured output validation
```

## Complete Headless Examples

### Basic Execution

```bash
# Simple prompt
claude --print --dangerously-skip-permissions "Explain what this file does: main.py"

# With specific model
claude --print --dangerously-skip-permissions --model sonnet "List all TODO comments"
```

### JSON Output for Parsing

```bash
# Single JSON result
claude --print --dangerously-skip-permissions --output-format json "Analyze this codebase"

# Streaming JSON
claude --print --dangerously-skip-permissions --output-format stream-json "Review this PR"
```

### Structured Output with Schema

```bash
# Enforce JSON structure
claude --print --dangerously-skip-permissions \
  --json-schema '{"type":"object","properties":{"summary":{"type":"string"},"issues":{"type":"array"}},"required":["summary","issues"]}' \
  "Analyze this code for bugs"
```

### Tool Restrictions

```bash
# Only allow reading files (no edits or bash)
claude --print --dangerously-skip-permissions --tools "Read,Glob,Grep" "Find all API endpoints"

# Allow git commands only
claude --print --dangerously-skip-permissions --allowedTools "Bash(git:*)" "Show recent commits"
```

### Piped Input

```bash
# Pipe code for review
cat main.py | claude --print --dangerously-skip-permissions "Review this code"

# Pipe diff for analysis
git diff | claude --print --dangerously-skip-permissions "Explain these changes"
```

### Budget-Limited Execution

```bash
# Limit API spend
claude --print --dangerously-skip-permissions --max-budget-usd 1.00 "Comprehensive code review"
```

### Session Continuation

```bash
# Continue previous session in headless mode
claude --print --dangerously-skip-permissions --continue "Now fix the bugs you identified"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error occurred |

## Security Considerations

1. **Only use `--dangerously-skip-permissions` in sandboxed environments**
2. Consider using `--tools` to restrict available capabilities
3. Use `--max-budget-usd` to prevent runaway costs
4. Review output before applying any suggested changes in production

## Python Integration Example

```python
import subprocess
import json

def run_claude_headless(prompt: str, output_format: str = "json") -> dict:
    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "--output-format", output_format,
        prompt
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Claude failed: {result.stderr}")

    if output_format == "json":
        return json.loads(result.stdout)
    return {"output": result.stdout}
```
