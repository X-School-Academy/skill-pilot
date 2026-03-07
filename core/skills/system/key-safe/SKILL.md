---
name: key-safe
description: Manage LLM security key protection for config/.env using core/bin/keys-safe-guard actions (enable, disable, get_key_names, put_key_values). Supports native GUI elevation for desktop sessions and clear fallback behavior for Python/background calls when safe guard is enabled.
---

# AI Builder - Key Safe

Manage secure key operations for `config/.env` using the project key safe command set.

## When to Use This Skill

- User asks to enable or disable env key safeguarding
- User asks to list available key names without exposing key values
- User asks to update or insert one or more env keys safely
- User asks for secure key operations related to LLM/provider credentials
- User asks to use a GUI popup / dialog for the sudo password prompt
- A Python or background process needs to read or write protected env keys

## Your Roles in This Skill

- **Security Engineer**: Enforce safe key handling and least-privilege behavior
- **Backend Developer (Engineer)**: Run key-safe command actions correctly
- **Technical Writer**: Report exactly what changed without leaking secret values

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Identify requested key-safe action

Map user intent to one action:

1. `enable` (default)
2. `disable`
3. `get_key_names`
4. `put_key_values`

### Step 2: Determine whether to use GUI mode

Add `--gui` when the user:
- Explicitly asks for a popup, dialog, or GUI password prompt
- Mentions they don't want to type their password in the terminal
- Asks for a "graphical" or "visual" sudo/auth prompt

`--gui` forces a native OS auth dialog for privilege elevation:
- **macOS**: system admin dialog via `osascript`
- **Linux**: `pkexec` (polkit) dialog, or `sudo -A` with `zenity`/`kdialog` askpass
- **No fallback**: if GUI is unavailable (SSH session, no display, dialog cancelled), the command fails instead of hanging on terminal `sudo`

`--gui` can be placed before or after the action name.

Important runtime behavior when safe guard is enabled and elevation is required:

- Interactive terminal session:
  - `core/bin/keys-safe-guard ...` uses terminal `sudo`
- Python/background process with a desktop GUI session:
  - `core/bin/keys-safe-guard ...` automatically opens a native GUI permission dialog, even without `--gui`
- Python/background process without a desktop GUI session:
  - the command cannot ask for a password interactively
  - tell the user to either configure passwordless sudo for the machine or disable safe guard first

### Step 3: Execute only the required action

From repo root, run:

```bash
core/bin/keys-safe-guard enable
core/bin/keys-safe-guard --gui enable
```

```bash
core/bin/keys-safe-guard disable
core/bin/keys-safe-guard --gui disable
```

```bash
core/bin/keys-safe-guard get_key_names
```

```bash
core/bin/keys-safe-guard put_key_values KEY1=VALUE1 KEY2=VALUE2
core/bin/keys-safe-guard --gui put_key_values KEY1=VALUE1 KEY2=VALUE2
```

Use exactly one action per user request unless the user explicitly asks for a sequence.

Note: `get_key_names` reads from engine memory and does not require elevated privileges — `--gui` has no effect on it.

### Step 4: Prevent secret leakage

- Never print key values in summaries
- For `get_key_names`, return names only
- For `put_key_values`, report which keys were updated, not their values

### Step 5: Report result and next state

Return:

1. Action executed
2. Success/failure status
3. Non-sensitive output summary
4. Any required next step (for example engine restart after safeguard changes)

## Expected Output

- Correct key-safe action execution
- No secret value disclosure
- Clear status message with concise next steps

## Key Principles

- Prefer minimal changes and single-action execution
- Keep secrets out of logs and responses
- Use `get_key_names` for inspection whenever values are not required
- Follow user constraints about password-prompting commands
- Use `--gui` when the user explicitly wants a popup/dialog, or when you know the command will run in a background/non-interactive desktop process
- If a protected key operation must run without a GUI and without a terminal, do not keep retrying; tell the user to set passwordless sudo or disable safe guard
