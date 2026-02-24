# Gemini CLI - Headless Mode Reference

Gemini CLI provides headless execution via positional prompts, which run in one-shot mode and exit after completion.

## Core Headless Command

```bash
gemini --yolo --sandbox "your prompt here"
```

## Essential Flags

| Flag | Description |
|------|-------------|
| Positional prompt | Query text triggers one-shot mode (required for headless) |
| `-y, --yolo` | Auto-accept all actions (required for full automation) |
| `-s, --sandbox` | Run in sandbox mode |
| `--approval-mode <mode>` | Alternative to --yolo for fine-grained control |

## Approval Modes (`--approval-mode`)

| Mode | Description |
|------|-------------|
| `default` | Prompt for approval (interactive) |
| `auto_edit` | Auto-approve edit tools only |
| `yolo` | Auto-approve all tools (same as --yolo) |

## Optional Configuration Flags

### Model Selection

```bash
-m, --model <model>        # Specify model to use
```

### Output Format

```bash
-o, --output-format <format>  # text, json, or stream-json
```

### Input Methods

```bash
-p, --prompt <prompt>      # Prompt via flag (deprecated, use positional)
-i, --prompt-interactive   # Execute prompt then continue interactively
```

### Extensions and Tools

```bash
-e, --extensions <list>    # Limit to specific extensions
-l, --list-extensions      # List available extensions
--allowed-mcp-server-names # Allowed MCP server names
--allowed-tools            # Tools allowed without confirmation
```

### Working Directory

```bash
--include-directories <dirs>  # Additional directories in workspace
```

### Session Management

```bash
-r, --resume <session>     # Resume session ("latest" or index)
--list-sessions            # List available sessions
--delete-session <index>   # Delete a session
```

### Debug and Accessibility

```bash
-d, --debug                # Enable debug mode
--screen-reader            # Enable screen reader mode
```

### Experimental

```bash
--experimental-acp         # Start in ACP mode
```

## Complete Headless Examples

### Basic Execution

```bash
# Simple one-shot execution
gemini "List all JavaScript files"

# With auto-approval
gemini --yolo "Fix the typo in index.html"
```

### Full Automation with Sandbox

```bash
# Recommended for automation
gemini --yolo --sandbox "Refactor the authentication module"
```

### JSON Output

```bash
# Get structured output
gemini --yolo --output-format json "Analyze this codebase structure"

# Streaming JSON
gemini --yolo --output-format stream-json "Review the code"
```

### Specific Model

```bash
# Use specific model
gemini --model gemini-2.0-flash --yolo "Explain this function"
```

### Limited Extensions

```bash
# Only use specific extensions
gemini --yolo --extensions files,search "Find security issues"
```

### Additional Directories

```bash
# Include extra directories
gemini --yolo --include-directories /path/to/libs "Check all dependencies"
```

### Auto-Approve Edits Only

```bash
# Auto-approve edits but ask for other actions
gemini --approval-mode auto_edit "Update the README"
```

### Piped Input

```bash
# Pipe content for analysis
cat main.py | gemini --yolo "Review this code"

# Pipe diff
git diff | gemini --yolo "Explain these changes"
```

### Resume Previous Session

```bash
# Continue from last session in headless mode
gemini --yolo --resume latest "Now apply the suggested fixes"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error occurred |

## Security Considerations

1. **Use `--sandbox`** whenever possible to limit filesystem access
2. **`--yolo` bypasses all confirmations** - only use in trusted environments
3. Use `--approval-mode auto_edit` for safer automation (edits only)
4. Consider using `--allowed-tools` to restrict capabilities

## Python Integration Example

```python
import subprocess
import json

def run_gemini_headless(prompt: str, output_format: str = "json") -> dict:
    cmd = [
        "gemini",
        "--yolo",
        "--sandbox",
        "--output-format", output_format,
        prompt
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Gemini failed: {result.stderr}")

    if output_format == "json":
        return json.loads(result.stdout)
    return {"output": result.stdout}
```

## Comparison: Interactive vs Headless

| Feature | Interactive | Headless |
|---------|-------------|----------|
| Prompt | None/flag | Positional argument |
| Approval | Per-action | `--yolo` or `--approval-mode` |
| Session | Persisted | One-shot (unless --resume) |
| Output | Terminal | Can be JSON/streamed |

## Notes

- The `-p, --prompt` flag is deprecated; use positional prompts instead
- Use `-i, --prompt-interactive` if you want to execute a prompt and then continue interactively
- Extensions can be listed with `gemini --list-extensions`
