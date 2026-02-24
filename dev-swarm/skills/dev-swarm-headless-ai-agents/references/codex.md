# Codex - Headless Mode Reference

Codex provides headless execution via the `exec` subcommand, which runs non-interactively and exits after completion.

## Core Headless Command

```bash
codex --ask-for-approval never --sandbox workspace-write exec "your prompt here"
```

## Essential Flags

| Flag | Description |
|------|-------------|
| `exec` | Run Codex non-interactively (subcommand, alias: `e`) |
| `-a, --ask-for-approval <policy>` | Configure approval behavior |
| `-s, --sandbox <mode>` | Sandbox policy for shell commands |

## Approval Policies (`--ask-for-approval`)

| Policy | Description |
|--------|-------------|
| `untrusted` | Only run "trusted" commands without approval |
| `on-failure` | Run all commands, ask only on failure |
| `on-request` | Model decides when to ask |
| `never` | Never ask for approval (full automation) |

## Sandbox Modes (`--sandbox`)

| Mode | Description |
|------|-------------|
| `read-only` | No write access |
| `workspace-write` | Write only to workspace |
| `danger-full-access` | Full filesystem access |

## Optional Configuration Flags

### Model Selection

```bash
-m, --model <model>        # Specify model to use
--oss                      # Use local open source model (LM Studio/Ollama)
--local-provider <provider> # Specify local provider (lmstudio, ollama, ollama-chat)
```

### Working Directory

```bash
-C, --cd <dir>             # Set working directory
--add-dir <dir>            # Additional writable directories
```

### Configuration Override

```bash
-c, --config <key=value>   # Override config values (dotted path supported)
-p, --profile <profile>    # Use configuration profile
```

### Features

```bash
--enable <feature>         # Enable a feature
--disable <feature>        # Disable a feature
--search                   # Enable live web search
```

### Input

```bash
-i, --image <file>...      # Attach images to prompt
```

### Dangerous Options

```bash
--dangerously-bypass-approvals-and-sandbox  # Skip ALL prompts and sandboxing (EXTREMELY DANGEROUS)
--full-auto                                  # Convenience alias (-a on-request, --sandbox workspace-write)
```

## Complete Headless Examples

### Basic Execution

```bash
# Simple non-interactive execution
codex exec "List all Python files in this project"

# With auto-approval
codex --ask-for-approval never --sandbox workspace-write exec "Fix the typo in README.md"
```

### Full Automation

```bash
# Complete automation with sandbox
codex --ask-for-approval never --sandbox workspace-write exec "Refactor the utils module"

# Full automation (alias)
codex --full-auto exec "Add error handling to main.py"
```

### Specific Model

```bash
# Use specific model
codex --model o3 --ask-for-approval never --sandbox workspace-write exec "Review this code"
```

### Read-Only Mode

```bash
# Analysis only (no writes)
codex --ask-for-approval never --sandbox read-only exec "Analyze the codebase architecture"
```

### With Images

```bash
# Analyze screenshot
codex --ask-for-approval never exec -i screenshot.png "What's wrong with this UI?"
```

### Working Directory

```bash
# Run in specific directory
codex -C /path/to/project --ask-for-approval never --sandbox workspace-write exec "Run tests"
```

### Local Model

```bash
# Use local LM Studio or Ollama
codex --oss --ask-for-approval never exec "Explain this function"
```

### Code Review (Dedicated Subcommand)

```bash
# Non-interactive code review
codex review
```

## Convenience Aliases

| Command | Equivalent |
|---------|------------|
| `codex e` | `codex exec` |
| `codex a` | `codex apply` |
| `codex --full-auto` | `--ask-for-approval on-request --sandbox workspace-write` |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error occurred |

## Security Considerations

1. **Prefer `--sandbox workspace-write`** over `danger-full-access`
2. **Never use `--dangerously-bypass-approvals-and-sandbox`** outside of externally sandboxed environments
3. Use `--sandbox read-only` for analysis-only tasks
4. Review generated diffs with `codex apply` before committing

## Python Integration Example

```python
import subprocess

def run_codex_headless(prompt: str, sandbox: str = "workspace-write") -> str:
    cmd = [
        "codex",
        "--ask-for-approval", "never",
        "--sandbox", sandbox,
        "exec",
        prompt
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Codex failed: {result.stderr}")

    return result.stdout
```

## Post-Execution

After headless execution, you can apply generated diffs:

```bash
# Apply the latest diff produced by Codex
codex apply

# Or review changes first
codex apply --dry-run  # If available
```
