# `keys-safe-guard` Action Reference

Detailed steps for the `core/bin/keys-safe-guard` command set. This is the **specialization** of the [general sudo rule](sudo-rule.md) for `config/.env` and explicit `.env`/`.env.*` operations — the binary handles GUI elevation internally; the agent only has to choose the right action and flags.

## Step 1: Identify requested action

Map user intent to exactly one action:

1. `enable` (default)
2. `disable`
3. `get_key_names`
4. `get_key_value`
5. `put_key_values`

Use one action per user request unless the user explicitly asks for a sequence.

## Step 2: Always use GUI mode for agent-invoked commands

**Rule:** if an AI agent invokes `core/bin/keys-safe-guard`, include `--gui` on every command unless the action is `get_key_names`. Apply this even when the user does not explicitly ask for a popup — do not wait to be told.

Why:
- AI agents should not depend on terminal password entry.
- GUI auth avoids hanging background or non-interactive runs.
- The project standard is to prefer native OS elevation dialogs whenever elevation might be needed.

What `--gui` does:
- **macOS**: system admin dialog via `osascript`.
- **Linux**: `pkexec` (polkit) dialog, or `sudo -A` with `zenity`/`kdialog` askpass.
- **No fallback**: if GUI is unavailable (SSH session, no display, dialog cancelled), the command fails instead of hanging on terminal `sudo`.

`--gui` may be placed before or after the action name.
`--env-file PATH` may also be placed before or after the action name. Omit it to use the default `config/.env`. Use it only when the user explicitly asks to manage another project env file.
`--auto-create` may also be placed before or after the action name. Use it only when the requested operation should create a missing env file.

Env file rules:

- Default: `config/.env`.
- Explicit target must stay inside the project and must be named `.env` or `.env.*`.
- `.env.example` is intentionally rejected by this skill because it is not a secret file.
- Missing files are not created by default. `--auto-create` creates the target env file with `600` permissions for `enable` and `put_key_values`; it does not apply to `disable`, `get_key_value`, or `get_key_names`.

Action rules:

| Action            | `--gui`           |
| ----------------- | ----------------- |
| `enable`          | always required   |
| `disable`         | always required   |
| `put_key_values`  | always required   |
| `get_key_value`   | required if the file may be guarded |
| `get_key_names`   | optional (no-op)  |

### Runtime behavior when safe guard is enabled and elevation is required

- **Interactive terminal session**:
  - Agent passing `--gui` → native GUI auth dialog.
  - Human running manually without `--gui` → may fall back to terminal `sudo`.
- **Python/background process with a desktop GUI session**:
  - `core/bin/keys-safe-guard ...` automatically opens a native GUI permission dialog, even without `--gui`.
- **Python/background process without a desktop GUI session**:
  - The command cannot ask for a password interactively.
  - Tell the user to either configure passwordless sudo for the machine or disable safe guard first. Do not keep retrying.

## Step 3: Execute the action

From repo root:

```bash
core/bin/keys-safe-guard --gui enable
```

```bash
core/bin/keys-safe-guard --gui disable
```

```bash
core/bin/keys-safe-guard get_key_names
```

```bash
core/bin/keys-safe-guard --gui get_key_value KEY1 KEY2
```

```bash
core/bin/keys-safe-guard --gui put_key_values KEY1=VALUE1 KEY2=VALUE2
```

Create the default env file if it is missing, then write keys:

```bash
core/bin/keys-safe-guard --gui --auto-create put_key_values KEY1=VALUE1
```

For a non-default env file:

```bash
core/bin/keys-safe-guard --gui --env-file path/to/.env.local get_key_value KEY1
```

```bash
core/bin/keys-safe-guard --gui --env-file path/to/.env.local put_key_values KEY1=VALUE1
```

```bash
core/bin/keys-safe-guard --gui --auto-create --env-file path/to/.env.local put_key_values KEY1=VALUE1
```

`get_key_names` reads from engine memory and does not require elevated privileges, so `--gui` is optional and has no effect for that action.

## Step 4: Prevent secret leakage

- Never print key values in summaries.
- For `get_key_names`, return **names only**.
- For `put_key_values`, report **which keys were updated**, not their values.
- Never echo, log, or persist the elevation password anywhere.

## Step 5: Report result and next state

Return:

1. Action executed.
2. Success/failure status.
3. Non-sensitive output summary.
4. Any required next step (for example, engine restart after safeguard changes).
