# General Sudo Command Rule (Agent)

This rule applies to **any** `sudo` command an AI agent needs to run — software installs (`sudo installer`, `sudo apt-get install`, `sudo snap install`, `sudo dnf install`, `sudo brew services`...), system config changes, file ownership/permission fixes, etc. It is **not** limited to `keys-safe-guard`.

The goal: never let an agent hang on an invisible terminal password prompt, never leak the password, and never run privileged commands the user did not authorize.

## Decision Order

For each individual sudo command, pick the first option that applies:

### 1. Passwordless sudo available

Detect with:

```bash
sudo -n true 2>/dev/null
```

If exit code is 0:
- Show the user the exact command you intend to run.
- Ask for one-time approval (unless the user has already pre-approved this kind of command in the current session or in `dev-swarm/user_preferences.md`).
- On approval, run `sudo <cmd>` directly.

### 2. GUI session available (and not over SSH)

Detect using the same logic as `skillpilot.sh::has_gui_env`:
- **macOS**: `/usr/bin/stat -f%Su /dev/console` returns a real user (not `root` / `loginwindow`) AND not inside SSH (`SSH_CONNECTION` / `SSH_TTY` unset).
- **Linux**: `DISPLAY` or `WAYLAND_DISPLAY` is set, or `loginctl show-session $XDG_SESSION_ID -p Type --value` reports `x11`/`wayland`, AND not SSH.

Then elevate via a native OS dialog:

- **macOS**:

  ```bash
  /usr/bin/osascript -e "do shell script \"<escaped cmd>\" with administrator privileges"
  ```

- **Linux** (try in order):
  1. `pkexec <cmd>`
  2. Fallback `sudo -A` with an askpass helper backed by `zenity --password` or `kdialog --password`.

Reference implementation lives in `skillpilot.sh::read_protected_file_with_gui` — reuse that pattern, do not invent a new one.

### 3. No passwordless sudo AND no GUI (SSH / headless / dialog cancelled)

Do **not** invoke `sudo` directly — it would block on a terminal prompt the agent cannot answer.

Instead:
1. Print the exact command, copy-paste ready, e.g.:

   ```
   Please run this in your terminal, then tell me when it's done:

     sudo apt-get install -y portaudio19-dev pkg-config
   ```

2. Wait for the user to confirm completion before continuing.
3. If the user reports failure, do not retry GUI mode in the same session — suggest either:
   - configuring passwordless sudo for the specific command via `/etc/sudoers.d/`, or
   - running the command from a GUI-capable session.

## Hard Rules

- **Never** run `sudo <cmd>` blindly in a non-interactive / background / agent context expecting a terminal password prompt to be answered.
- **Never** ask the user to paste their sudo password into the chat. Always go through the OS dialog, passwordless sudo, or manual terminal execution.
- **Never** log, echo, or persist the sudo password anywhere.
- Bracket sensitive elevated reads with `sudo -k` before and after (see `skillpilot.sh:1461-1463`) when not using the GUI path.
- One sudo command per approval. Do not batch unrelated privileged operations behind a single prompt — the user should see what they are authorizing.
- Prefer the **least-privilege** form of the command (e.g., `sudo -u _user cmd` over a full root shell; targeted package install over `apt-get dist-upgrade`).

## Examples

**macOS — install a `.pkg`:**

```bash
# GUI path (preferred when at the console)
/usr/bin/osascript -e 'do shell script "installer -pkg /tmp/foo.pkg -target /" with administrator privileges'
```

**Linux desktop — install a package:**

```bash
# Preferred
pkexec apt-get install -y ripgrep
# Fallback (askpass)
SUDO_ASKPASS=/tmp/askpass.sh sudo -A apt-get install -y ripgrep
```

**SSH session — no GUI, no passwordless sudo:**

```
Please run this on the host yourself:

  sudo snap install --classic code

Reply 'done' when the install finishes.
```

## Relation to `keys-safe-guard`

`keys-safe-guard` is the **specialization** of this rule for `config/.env` operations:
- It already implements the GUI elevation pattern internally.
- The agent only has to add `--gui` for `enable` / `disable` / `put_key_values` (see the main `SKILL.md`).

For every **other** sudo need (software installs, system tweaks, log inspection, etc.), follow the decision order above.
