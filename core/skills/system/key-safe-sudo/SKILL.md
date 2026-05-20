---
name: key-safe-sudo
description: Manage LLM security key protection for config/.env using core/bin/keys-safe-guard actions (enable, disable, get_key_names, put_key_values), and govern all other agent-invoked sudo commands (software installs, system config) via the general sudo rule. Prefers native GUI elevation; never relies on hidden terminal password prompts.
---

# AI Builder - Key Safe

Manage secure key operations for `config/.env` and govern any privileged (`sudo`) action an agent needs to run.

## When to Use This Skill

- User asks to enable or disable env key safeguarding.
- User asks to list available key names without exposing key values.
- User asks to update or insert one or more env keys safely.
- User asks for secure key operations related to LLM/provider credentials.
- User asks to use a GUI popup / dialog for a sudo password prompt.
- A Python or background process needs to read or write protected env keys.
- **Any time the agent needs to run a `sudo` command** (e.g. `sudo installer`, `sudo apt-get install`, `sudo snap install`, `sudo dnf install`, ownership/permission fixes) — apply the general sudo rule before invoking it.

## Your Roles in This Skill

- **Security Engineer**: Enforce safe key handling and least-privilege behavior.
- **Backend Developer (Engineer)**: Run key-safe command actions correctly.
- **Technical Writer**: Report exactly what changed without leaking secret values.

## Role Communication

Announce actions before performing them, using:

> As a {Role, and Role-XYZ if more roles}, I will {action description}

This keeps human-in-the-loop oversight at key decision points.

## General Sudo Rule

For **any** agent-invoked `sudo` command, follow [references/sudo-rule.md](references/sudo-rule.md). Decision order:

1. **Passwordless sudo available** (`sudo -n true` exits 0) → show the command, get one-time user approval, run directly.
2. **GUI session available** (desktop console, not SSH) → elevate via native dialog (`osascript … with administrator privileges` on macOS; `pkexec` or `sudo -A` with `zenity`/`kdialog` askpass on Linux).
3. **Otherwise (SSH / headless)** → print the exact command for the user to run manually and wait. Do **not** invoke `sudo` directly.

Never ask the user to paste a sudo password into chat, never log it, never batch unrelated privileged operations behind one approval. See the reference for examples and detection details.

## `keys-safe-guard` Operations

For `config/.env` actions — `enable`, `disable`, `get_key_names`, `put_key_values` — follow [references/keys-safe-guard.md](references/keys-safe-guard.md). Quick summary:

- Use **`--gui`** for `enable`, `disable`, `put_key_values` (mandatory for agent-invoked runs).
- `--gui` is optional for `get_key_names` (read-only, in-memory).
- In a non-GUI environment, do not retry — tell the user to configure passwordless sudo or disable safe guard from a GUI-capable session.

## Expected Output

- Correct action execution.
- No secret value disclosure.
- Clear status message with concise next steps (e.g. engine restart after safeguard changes).

## Key Principles

- Prefer minimal changes and single-action execution.
- Keep secrets out of logs and responses; never print key values.
- Use `get_key_names` for inspection whenever values are not required.
- Treat `--gui` as mandatory for every agent-invoked `keys-safe-guard` action except `get_key_names`.
- Do not rely on terminal password prompts for agent-driven privileged work — use GUI dialog, passwordless sudo, or hand the command back to the user.
- Do not keep retrying when the environment cannot elevate; surface the constraint and the fix.
