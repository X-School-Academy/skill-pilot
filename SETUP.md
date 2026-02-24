# Skill Pilot Manual Setup (macOS and Linux)

Use this guide if `install.sh` or `skillpilot.sh` init cannot finish automatically.

## 0. Prerequisites

- Supported OS: macOS or Linux (Windows users should use WSL first).
- Have at least one ready:
1. Claude Code, Codex, Gemini CLI, or OpenCode CLI
2. OpenAI-compatible or Claude-compatible API URL and key

If you have neither an agent CLI nor API credentials, setup cannot complete.

## 1. Install Homebrew (if missing)

`install.sh` uses Homebrew as the package manager baseline.

```bash
NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL --proto '=https' --tlsv1.2 https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After install, load Homebrew into your current shell:

Apple Silicon macOS:

```bash
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Intel macOS:

```bash
eval "$(/usr/local/bin/brew shellenv)"
```

Linuxbrew:

```bash
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

## 2. Install base tools and runtimes

Install base packages with Homebrew:

```bash
brew install git curl tmux
```

Install `uv` using the official script (same method as `install.sh`):

```bash
curl -fsSL --proto '=https' --tlsv1.2 https://astral.sh/uv/install.sh | sh
```

Install `pnpm` using the official script (same method as `install.sh`):

```bash
curl -fsSL --proto '=https' --tlsv1.2 https://get.pnpm.io/install.sh | sh
```

Set `PNPM_HOME` and update `PATH`:

macOS:

```bash
export PNPM_HOME="${PNPM_HOME:-$HOME/Library/pnpm}"
export PATH="$PNPM_HOME:$PATH"
```

Linux:

```bash
export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}"
export PATH="$PNPM_HOME:$PATH"
```

Install Node.js LTS (required: Node 18+):

```bash
pnpm env use --global lts
```

Install Python 3.9+ (if missing):

```bash
uv python install
```

Install Playwright CLI:

```bash
pnpm install -g @playwright/cli@latest
```

## 3. Install at least one AI code agent CLI

Supported providers checked by `skillpilot.sh`:

- `claude`
- `codex`
- `gemini`
- `opencode`

Install commands used by the init flow:

```bash
curl -fsSL https://claude.ai/install.sh | bash
brew install codex
```

Notes:

- `brew install codex` requires Homebrew.
- For Gemini CLI and OpenCode CLI, install from their official docs, then verify with:

```bash
command -v gemini
command -v opencode
```

## 4. Clone repo and set up branches

After cloning, the default branch is `codeware` (stable release layer).
Create local working branches and switch to `user` before making changes.

Short meanings:
- `codeware`: stock software baseline (stable upstream branch)
- `contrib`: branch for opening pull requests to share improvements
- `user`: your personal workspace branch for daily AI/user edits

```bash
git clone https://github.com/x-school-academy/skill-pilot "$HOME/workspace/skill-pilot"
cd "$HOME/workspace/skill-pilot"

# default branch after clone: codeware
git branch contrib
git branch user
git checkout user
```

If `contrib` or `user` already exists, skip creating that branch.

## 5. Install project dependencies

From repo root:

```bash
uv --project core/engine sync
pnpm -C core/webui install
```

## 6. Create `config/.env`

Create `config/.env` with at minimum:

```dotenv
ONLY_ALLOW_HTTPS=0
AUTH_TOKEN=<uuid-or-random-secret>
```

Generate a UUID token:

```bash
core/engine/.venv/bin/python - <<'PY'
import uuid
print(uuid.uuid4())
PY
```

Add provider credentials for your selected provider (if needed):

OpenAI-compatible:

```dotenv
OPENAI_BASE_URL=https://your-openai-compatible-endpoint
OPENAI_API_KEY=<your-openai-key>
```

Claude-compatible:

```dotenv
ANTHROPIC_BASE_URL=https://your-claude-compatible-endpoint
ANTHROPIC_AUTH_TOKEN=<your-claude-token>
ANTHROPIC_API_KEY=
```

Recommended permission:

```bash
chmod 600 config/.env
```

## 7. Update `config/settings.json5`

Set host and service ports (example):

```json5
{
  "services": {
    "engine": {
      "host": "127.0.0.1",
      "port": 3001
    },
    "webui": {
      "host": "127.0.0.1",
      "port": 3000
    }
  }
}
```

If binding to non-localhost hosts, decide whether to enforce HTTPS (`ONLY_ALLOW_HTTPS=1`) or allow HTTP (`ONLY_ALLOW_HTTPS=0`).

## 8. Update `config/ai_providers.json5`

- Set `default.llm` to your chosen provider id:
  - Native CLI mode: `claude`, `codex`, `gemini`, or `opencode`
  - Compatible API mode: `claude-compat` or `codex-compat`
- Set `disabled: true` for unused LLM providers.
- Keep your selected provider enabled (`disabled: false` or omit `disabled`).

Compatibility mapping used by `skillpilot.sh` init:

- If you pick `claude` and provide a Claude-compatible API URL/key, default becomes `claude-compat`.
- If you pick `codex` and provide an OpenAI-compatible API URL/key, default becomes `codex-compat`.
- `opencode` can also use OpenAI-compatible env vars, but provider id remains `opencode`.

## 9. Start services

Development mode:

```bash
./skillpilot.sh start --dev
```

Production mode:

```bash
./skillpilot.sh start
```

Stop services:

```bash
./skillpilot.sh stop
```

## Notes

- `skillpilot.sh` auto-runs an interactive init wizard when `config/.env` is missing.
- The wizard updates `config/.env`, `config/settings.json5`, and `config/ai_providers.json5` using Python from `core/engine/.venv` when available.
