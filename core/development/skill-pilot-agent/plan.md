# Skill Pilot Agent Development Plan

## Requirement Summary

Create a new Skill Pilot agent under `core/engine/skill_pilot_agent/`, backed by the `openai-agents` package and an OpenAI-compatible endpoint configured with:

- `SKILL_PILOT_BASE_URL`
- `SKILL_PILOT_API_KEY`
- `SKILL_PILOT_MODEL`

Expose the agent through `core/bin/skill-pilot-agent`, add it to `config/ai_providers.json5`, and support `default.background_llm: 'skill-pilot'` so non-tmux background LLM tasks can use it. The agent should respect the root `AGENTS.md` instructions from `--agent-dir`, and should only expose bash commands as tools.

## Approved Decisions

- The Skill Pilot provider is selected only when `default.background_llm` is set to `'skill-pilot'`; it is not the normal default LLM provider.
- `SKILL_PILOT_MODEL` provides the default model, and `--model <model>` overrides it.
- This feature adds key support only; `default.background_llm` remains unset by default.
- `--network no` should use strict OS-level enforcement when available. If strict enforcement is not available, fail safely.
- `--skills-dir` and `--skills` must load skill instructions in the first release.

## Existing Integration Points

- `config/ai_providers.json5` defines CLI-backed LLM providers and default provider selections.
- `core/engine/llm_service.py` loads provider config, builds non-interactive LLM commands, resolves provider env, parses CLI output, and provides `llm_get_text`, `llm_get_json`, and `llm_stream`.
- `core/engine/routes.py` builds terminal/tmux provider commands separately through terminal-specific paths; this should continue using normal LLM provider selection, not `default.background_llm`.
- `core/bin/skill-agent` shows the existing wrapper pattern: resolve repo root, `cd` there, then run a Python module through `uv --directory core/engine run`.
- `core/engine/tests/test_llm_service.py` already covers provider argument construction and parsing behavior.

## Proposed Design

### 1. Add Python Package

Create `core/engine/skill_pilot_agent/` with a small CLI-oriented package:

- `__init__.py`
- `cli.py`
- `agent.py`
- `agents_md.py`
- `bash_tool.py`

Responsibilities:

- Parse the required CLI arguments.
- Convert the incoming prompt into a single task for the agent.
- Load the root `AGENTS.md` instructions directly under `--agent-dir`.
- Configure `openai-agents` to use `SKILL_PILOT_BASE_URL` and `SKILL_PILOT_API_KEY`.
- Register only bash-command tooling.
- Print assistant text to stdout in a format compatible with current `llm_service.py` parsing.

### 2. Add CLI Wrapper

Create `core/bin/skill-pilot-agent` following the existing wrapper style:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "$REPO_ROOT"
exec uv --directory core/engine run python -m skill_pilot_agent.cli "$@"
```

Make it executable.

### 3. Add Dependency

Update `core/engine/pyproject.toml`:

- Add `openai-agents` to project dependencies.
- Refresh `core/engine/uv.lock` through `uv lock` or the project-standard equivalent.

### 4. Add Provider Config

Update `config/ai_providers.json5`:

- Add optional default key:

```json5
default: {
  llm: 'claude',
  doctor: 'opencode',
  background_llm: '',
  tts: 'media-mcp',
  image: 'media-mcp',
}
```

- Add an LLM provider:

```json5
{
  id: 'skill-pilot',
  name: 'Skill Pilot Agent',
  bin: 'core/bin/skill-pilot-agent',
  'background-only': true,
  'sandbox-args': ['--sandbox', 'yes'],
  'auto-args': ['--auto', 'yes'],
  'network-args': ['--network', 'yes'],
  args: ['--model', '${SKILL_PILOT_MODEL}', '{{prompt}}'],
  env: {
    'SKILL_PILOT_BASE_URL': '${SKILL_PILOT_BASE_URL}',
    'SKILL_PILOT_API_KEY': '${SKILL_PILOT_API_KEY}',
    'SKILL_PILOT_MODEL': '${SKILL_PILOT_MODEL}',
    'PLAYWRIGHT_MCP_EXTENSION_TOKEN': '${PLAYWRIGHT_MCP_EXTENSION_TOKEN}',
  },
}
```

Note: the provider can be disabled by default if approval prefers avoiding accidental selection before env vars are configured.

### 5. Route Background LLM Tasks

Update `core/engine/llm_service.py`:

- Add `get_default_background_llm_provider_id()`.
- Add a provider-selection helper for background calls:
  - If `provider_id` is explicitly passed, keep using it.
  - If no `provider_id` is passed and `default.background_llm == 'skill-pilot'`, select `skill-pilot`.
  - If missing, disabled, or invalid, fall back to `default.llm`.
- Apply the background selection to `llm_get_text`, `llm_get_json`, and `llm_stream`.
- Do not apply this to terminal/tmux command building; tmux sessions should continue using `get_provider(provider_id)` through existing route logic.

### 6. Implement CLI Arguments

Support these arguments with defaults:

- `--sandbox yes|no`, default `yes`
- `--auto yes|no`, default `yes`
- `--network yes|no`, default `no`
- `--model <model>`, defaults to `SKILL_PILOT_MODEL`
- `--agent-dir <path>`, default project root/current working directory
- `--log-level <level>`, default `info`
- `--max-retries <number>`, default `3`
- `--timeout <seconds>`, default `60`
- `--bash-commands <command1,command2,...>`, default all available commands
- `--skills-dir <path>`, default `.agent` under the project root
- `--skills <skill1,skill2,...>`, default all available skills

For this first implementation, only default behavior for `sandbox`, `auto`, and `network` is required. Non-default values should be parsed and logged, but can return a clear unsupported message if they require behavior not yet implemented.

### 7. Bash Tool Scope

Implement one bash tool with these controls:

- Runs commands relative to `--agent-dir`.
- If `--bash-commands` is provided, only allow commands whose executable name is in the allowlist.
- If `--network no`, do not grant any special network permission. If stronger enforcement is needed, fail fast for known network tools such as `curl`, `wget`, package installers, and browser launchers.
- If `--sandbox yes`, keep command execution under the normal project process environment and do not add elevated permissions.
- Capture stdout, stderr, and exit code for the agent.

### 8. AGENTS.md Loading

Implement deterministic instruction loading:

- Load only `<agent-dir>/AGENTS.md`.
- Do not recursively load nested `AGENTS.md` files.
- If subdirectory-specific instructions are needed later, add them to the task-specific system prompt or load them selectively for the active task context.

### 9. Tests

Add focused tests:

- `core/engine/tests/test_llm_service.py`
  - `default.background_llm` selects `skill-pilot` for background calls when no provider is explicit.
  - explicit `provider_id` overrides `background_llm`.
  - terminal command construction does not silently switch to `skill-pilot`.
  - provider env expansion includes `SKILL_PILOT_BASE_URL` and `SKILL_PILOT_API_KEY`.
- New `core/engine/tests/test_skill_pilot_agent_cli.py`
  - argument defaults parse correctly.
  - invalid yes/no values fail clearly.
  - `--bash-commands` allowlist blocks disallowed executables.
  - AGENTS.md loading skips ignored paths.

Manual smoke checks:

```bash
core/bin/skill-pilot-agent "Reply with OK"
SKILL_PILOT_BASE_URL=http://localhost:8000/v1 SKILL_PILOT_API_KEY=test core/bin/skill-pilot-agent "Reply with OK"
uv --directory core/engine run pytest core/engine/tests/test_llm_service.py
uv --directory core/engine run pytest core/engine/tests/test_skill_pilot_agent_cli.py
```

## Touched Files

Expected new files:

- `core/bin/skill-pilot-agent`
- `core/engine/skill_pilot_agent/__init__.py`
- `core/engine/skill_pilot_agent/cli.py`
- `core/engine/skill_pilot_agent/agent.py`
- `core/engine/skill_pilot_agent/agents_md.py`
- `core/engine/skill_pilot_agent/bash_tool.py`
- `core/engine/skill_pilot_agent/ignore_rules.py`
- `core/engine/skill_pilot_agent/skills.py`
- `core/engine/tests/test_skill_pilot_agent_cli.py`

Expected modified files:

- `config/ai_providers.json5`
- `core/engine/pyproject.toml`
- `core/engine/uv.lock`
- `core/engine/llm_service.py`
- `core/engine/tests/test_llm_service.py`

## Acceptance Criteria

- `core/bin/skill-pilot-agent` exists, is executable, and can accept the documented arguments.
- The new agent package uses `SKILL_PILOT_BASE_URL` and `SKILL_PILOT_API_KEY` for an OpenAI-compatible endpoint.
- The agent exposes only bash commands as tools.
- The agent loads only the root `AGENTS.md` under `--agent-dir`.
- `default.background_llm: 'skill-pilot'` routes non-tmux background LLM tasks to Skill Pilot.
- tmux terminal sessions continue using the existing provider selection behavior.
- Tests cover config routing, CLI argument parsing, bash allowlisting, and AGENTS.md loading.

## Resolved Questions

1. Provider selection is controlled by `default.background_llm == 'skill-pilot'`.
2. The model defaults to `SKILL_PILOT_MODEL`; `--model` overrides it.
3. The config supports `default.background_llm`, but leaves it unset by default.
4. `--network no` uses strict OS-level enforcement when available, otherwise fails safely.
5. `--skills-dir` and `--skills` load skill instructions in the first release.
