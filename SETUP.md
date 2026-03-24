# Skill Pilot Manual Setup (macOS and Linux)

Use this guide if `install.sh` or `skillpilot.sh` init cannot finish automatically.

## 0. Prerequisites

- Supported OS: macOS or Linux (Windows users should use WSL first).
- Have at least one ready:
1. Claude Code, GitHub Copilot CLI, Codex, Gemini CLI, or OpenCode CLI
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

Install agent-browser CLI:

```bash
pnpm install -g agent-browser
```

## 3. Install at least one AI code agent CLI

Supported providers checked by `skillpilot.sh`:

- `claude`
- `copilot`
- `codex`
- `gemini`
- `opencode`

Install commands used by the init flow:

```bash
curl -fsSL https://claude.ai/install.sh | bash
pnpm install -g @github/copilot
pnpm install -g @openai/codex
pnpm install -g @google/gemini-cli
pnpm install -g opencode-ai
```

Notes:

- `pnpm install -g ...` requires `pnpm` and a working Node.js installation.
- Verify installed CLIs with:

```bash
command -v claude
command -v copilot
command -v codex
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

Add provider credentials for your selected provider (if needed). The compatible API and Ollama providers in `config/ai_providers.json5` read these env vars directly:

OpenAI-compatible for `codex-compat`:

```dotenv
OPENAI_COMPAT_BASE_URL=https://your-openai-compatible-endpoint
OPENAI_COMPAT_API_KEY=<your-openai-key>
```

Claude-compatible for `claude-compat`:

```dotenv
ANTHROPIC_COMPAT_BASE_URL=https://your-claude-compatible-endpoint
ANTHROPIC_COMPAT_AUTH_TOKEN=<your-claude-token>
ANTHROPIC_API_KEY=
```

Ollama:

```dotenv
# Defaults already point to local Ollama in config/ai_providers.json5
# Change only if your Ollama endpoint differs.
OPENAI_BASE_URL=http://localhost:11434/v1/
OPENAI_API_KEY=ollama
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
      "production": {
        "port": 3001
      },
      "development": {
        "port": 3002
      }
    },
    "webui": {
      "host": "127.0.0.1",
      "development": {
        "port": 3003
      }
    }
  }
}
```

If binding to non-localhost hosts, decide whether to enforce HTTPS (`ONLY_ALLOW_HTTPS=1`) or allow HTTP (`ONLY_ALLOW_HTTPS=0`).

Port meanings:

- `engine.production.port`: production engine and bundled release WebUI, default `3001`
- `engine.development.port`: development engine, default `3002`
- `webui.development.port`: Next.js development WebUI, default `3003`

## 8. Update `config/ai_providers.json5`

- Set `default.llm` to your chosen provider id:
  - Native CLI mode: `claude`, `copilot`, `codex`, `gemini`, or `opencode`
  - Compatible API mode: `claude-compat` or `codex-compat`
  - Local Ollama mode: `ollama`
- Set `disabled: true` for unused LLM providers.
- Keep your selected provider enabled (`disabled: false` or omit `disabled`).
- The built-in compatible providers are disabled by default. To enable one, edit its entry under `llm` and either remove `disabled: true` or change it to `disabled: false`.

Example selections:

```json5
default: {
  llm: 'ollama',
  tts: 'openai',
  image: 'openai',
}
```

```json5
{
  id: 'ollama',
  disabled: false,
  model: 'llama3.2',
  env: {
    OPENAI_API_KEY: 'ollama',
    OPENAI_BASE_URL: 'http://localhost:11434/v1/',
  },
}
```

## 9. Start Skill Pilot

Production mode:

```bash
./skillpilot.sh
```

Development mode:

```bash
./skillpilot.sh --dev
```

Run both at the same time:

```bash
./skillpilot.sh
./skillpilot.sh --dev
```

Stop production only:

```bash
./skillpilot.sh stop
```

Stop development only:

```bash
./skillpilot.sh stop --dev
```

## 10. Using AI Agent CLIs Directly

If you use AI agent CLIs directly, without the Skill Pilot WebUI:

- Use production mode by starting the engine with `./skillpilot.sh`
- During development, export `SKILL_PILOT_RUNTIME_MODE=development` before starting the agent CLI directly

Examples:

```bash
export SKILL_PILOT_RUNTIME_MODE=development
claude
```

```bash
export SKILL_PILOT_RUNTIME_MODE=development
codex
```

```bash
export SKILL_PILOT_RUNTIME_MODE=development
gemini
```

The same rule applies to other supported agent CLIs such as Copilot CLI or OpenCode.

```json5
{
  id: 'codex-compat',
  disabled: false,
  model: 'your-openai-compatible-model',
}
```

```json5
{
  id: 'claude-compat',
  disabled: false,
  model: 'your-claude-compatible-model',
}
```

Provider notes:

- `claude-compat` reads `ANTHROPIC_COMPAT_BASE_URL` and `ANTHROPIC_COMPAT_AUTH_TOKEN`.
- `codex-compat` reads `OPENAI_COMPAT_BASE_URL` and `OPENAI_COMPAT_API_KEY`.
- `ollama` is preconfigured to use `http://localhost:11434/v1/` via the Codex CLI adapter; update its `model` to the Ollama model you actually installed.
- `opencode` can also be pointed at an OpenAI-compatible endpoint by editing its `env` block in `config/ai_providers.json5`.

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

## 10. Optional dependency packs

Enable optional features only when needed:

```bash
./skillpilot.sh enable human-detection
./skillpilot.sh enable live-tts
```

`enable live-tts` installs OS audio build dependencies (PortAudio + pkg-config) on macOS/Linux and then installs Python packages from `core/engine/mcp_servers/live_tts/requirements-live-tts.txt`.

Disable optional packs:

```bash
./skillpilot.sh disable human-detection
./skillpilot.sh disable live-tts
```

## Notes

- `skillpilot.sh` auto-runs an interactive init wizard when `config/.env` is missing.
- The wizard updates `config/.env`, `config/settings.json5`, and `config/ai_providers.json5` using Python from `core/engine/.venv` when available.
