---
name: key-safe
description: Manage LLM security key protection for config/.env using core/bin/keys-safe-guard actions (enable, disable, get_key_names, put_key_values). Supports --gui flag for native OS auth dialogs (macOS osascript, Linux pkexec/zenity/kdialog). Use when the user asks to secure, inspect, or update protected env keys safely, with or without a GUI password prompt.
---

# AI Builder - Key Safe

Manage secure key operations for `config/.env` using the project key safe command set.

## When to Use This Skill

- User asks to enable or disable env key safeguarding
- User asks to list available key names without exposing key values
- User asks to update or insert one or more env keys safely
- User asks for secure key operations related to LLM/provider credentials
- User asks to use a GUI popup / dialog for the sudo password prompt

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

`--gui` triggers a native OS auth dialog for privilege elevation:
- **macOS**: system admin dialog via `osascript`
- **Linux**: `pkexec` (polkit) dialog, or `sudo -A` with `zenity`/`kdialog` askpass
- **Fallback**: if GUI is unavailable (SSH session, no display, dialog cancelled), it falls back silently to terminal `sudo`

`--gui` can be placed before or after the action name.

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

### Step 6: Reload engine after key updates

If action is `put_key_values`, `enable`, or `disable`, apply engine reload so in-memory env is synchronized:

```bash
core/bin/tool-cli engine-reload
```

Use system skill `core-engine` for this operation flow.

## Expected Output

- Correct key-safe action execution
- No secret value disclosure
- Clear status message with concise next steps

## Key Principles

- Prefer minimal changes and single-action execution
- Keep secrets out of logs and responses
- Use `get_key_names` for inspection whenever values are not required
- Follow user constraints about password-prompting commands
- Use `--gui` when the user asks for a popup/dialog prompt; otherwise omit it and let terminal sudo handle authentication
