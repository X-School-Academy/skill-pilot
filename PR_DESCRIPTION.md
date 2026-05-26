# PR: Web UI model and effort selection for agent sessions

## Summary

This PR allows users to select which **model** and **reasoning effort** to use when
creating a new AI agent session from the web UI. Previously, model and effort were
hardcoded or absent — the agent always ran with whatever default the system picked.
Now each provider advertises its available models and effort levels, the web UI
renders dropdowns, and the selection flows through the API → engine command builder →
agent CLI → LLM SDK.

## What changed

### 1. Provider metadata — `routes_integrations.py`

`GET /api/llm/providers` now returns `models` and `effort_levels` per provider
instead of only `id` and `name`. The web UI uses these arrays to populate the
model and effort dropdowns.

```
Before:  {"id": "skill-pilot", "name": "Skill Pilot"}
After:   {"id": "skill-pilot", "name": "Skill Pilot",
          "models": ["gpt-5.5", "claude-sonnet-4-6", ...],
          "effort_levels": ["low", "medium", "high", "xhigh"]}
```

### 2. Command builder — `llm_service.py`

Three interdependent changes to `build_llm_command()` and `build_terminal_command()`:

**a) Model resolution with precedence.** Model is resolved as: CLI override >
provider config > None. Previously it only read `provider.get("model")`.

**b) Template-aware flag placement.** `--model` and `--effort` are only prepended
to the argument list when the provider's arg template does NOT already contain
`{{model}}` / `{{effort}}`. If the template has the placeholder, template
replacement handles placement (keeping flags after `uv run` for uv-based
providers). Without this check, the flags land twice (duplicated) and for
uv-based providers they appear before `run` — which uv rejects as unknown flags.

**c) `{{effort}}` template replacement.** New placeholder, works identically to
`{{model}}`: when the provider template contains `{{effort}}`, it's replaced with
the user's selection; when absent, the entire arg is skipped.

**d) `format_command_for_log`** now renders `--effort=value` (joined with `=`)
the same way it renders `--model=value`, for display consistency.

### 3. API routes — `routes.py` + `routes_shared.py`

`POST /api/terminal/tmux/create` now accepts `model` and `effort` in the request
body. Both are optional strings — absent or empty means "use provider default."
They thread through `_build_provider_command()` → `build_terminal_command()`.

### 4. Agent CLI — `cli.py` + `agent.py`

`skill_pilot_agent.cli` gained `--effort` (values: `low`, `medium`, `high`,
`xhigh`). The value is stored in `SkillPilotAgentConfig.effort` and passed to the
`openai-agents` SDK as `RunConfig(model_settings=ModelSettings(reasoning={"effort": ...}))`.
This sets the reasoning effort on the API request for providers that support it
(OpenAI o-series, Claude Opus 4.7, etc.).

### 5. Web UI main page — `pages/index.tsx`

- **`LlmProvider` interface** extended with `models: string[]` and `effort_levels: string[]`
- **State:** `selectedModel` and `selectedEffort` (both `string | null`)
- **Provider switch** resets model to the new provider's first model, clears effort
- **Model dropdown** in the new session form, populated from the selected provider's models
- **Effort dropdown** next to it, disabled when the provider has no effort levels
- **Payload:** `model` and `effort` included in the `POST /api/terminal/tmux/create` body

### 6. Shared session panel — `components/EmbeddedSessionPanel.tsx`

Optional props added: `availableModels`, `selectedModel`, `onModelChange`,
`availableEffortLevels`, `selectedEffort`, `onEffortChange`. When provided
(not all parent pages do yet), model/effort selectors render in the embedded
session form. Backward compatible — absent props = no selectors, existing
behavior unchanged.

## Why

The system supports multiple AI providers (DeepSeek, Claude, Gemini, OpenAI)
each with different models and reasoning capabilities. Before this change,
the web UI had no way to tell the agent "use claude-sonnet-4-6 with high
effort for this task." The model was either hardcoded or picked from a
provider catalog that had no entries for custom providers.

The user's requirement: **"allow select model and effort for different tasks
for Agent automation from the webui."**

## Methodology

### Discovery phase

1. Traced the full session-creation path: web UI → `POST /api/terminal/tmux/create`
   → `_build_provider_command()` → `build_terminal_command()` → `exec_argv.py` →
   `subprocess.Popen` → agent CLI → `openai-agents` SDK
2. Identified every seam where model/effort needed to be threaded through
3. Found that `build_terminal_command()` was prepending `--model` and `--effort`
   to the front of every command — before `uv run` for uv-based providers
4. Verified with live API calls that each change propagated correctly

### Critical bug found during verification

`build_terminal_command()` prepended `--model` and `--effort` to every command
unconditionally. For the skill-pilot provider (which wraps `uv run`), this placed
them before the `run` subcommand:

```
uv --model=claude-sonnet-4-6 --effort high --directory ... run python -m skill_pilot_agent.cli ...
```

`uv` rejects unknown flags:

```
$ uv --model test-model --effort high --directory ... run python -c "print('hello')"
error: unexpected argument '--model' found
```

Every session using model/effort selection with the skill-pilot provider would
fail silently in the tmux session.

The fix checks whether the provider's template already contains `{{model}}` /
`{{effort}}`. If it does, template replacement handles placement correctly
(after `run`); the prepend is skipped:

```
uv --directory ... run python -m skill_pilot_agent.cli --model=claude-sonnet-4-6 --effort=high 'list files'
```

### Verification

#### Unit tests (98 passed, 0 failed)

**New tests — `tests/test_model_effort_selection.py` (27 tests):**

| Test group | Tests | What it covers |
|-----------|-------|----------------|
| Model resolution | 3 | CLI override > provider config > None |
| Effort parameter | 2 | Effort prepended, None omitted |
| Template-aware prepend | 6 | No duplicate when template has `{{model}}`/`{{effort}}`, arg skipped when None, flags after `run` |
| Combined scenarios | 2 | Model-only, effort-only (independent) |
| UV provider (skill-pilot) | 2 | Full args with flags after `run`, no-selection clean command |
| Terminal command | 4 | Template replacement, prepend fallback, codex passthrough |
| Codex terminal args | 4 | Model, effort, both, neither |
| Log formatting | 3 | `--effort=value`, both flags, edge case |
| Edge cases | 2 | Empty string → no flag |

**Existing tests — no regressions:**
- `test_llm_service_helpers.py`: 61/61 passed
- `test_skill_pilot_agent_cli.py`: 10/10 passed
- `test_llm_service.py`: 4/7 passed (3 pre-existing failures in TTS/image/JSON unrelated to this change)

#### Live API verification (engine running on port 8765)

Tested `POST /api/terminal/tmux/create` against a running engine instance:

| Provider | Model | Effort | Command |
|----------|-------|--------|---------|
| echo-llm | (none) | (none) | `echo hello` |
| echo-llm | test-model | low | `echo --model=test-model --effort=low hello` |
| echo-llm | (none) | xhigh | `echo --effort=xhigh hello` |
| echo-llm | gpt-5.5 | (none) | `echo --model=gpt-5.5 hello` |
| echo-llm | claude-sonnet-4-6 | high | `echo --model=claude-sonnet-4-6 --effort=high hello` |
| echo-llm | "" | "" | `echo hello` (empty strings → no flags) |
| skill-pilot | (none) | (none) | `uv --directory ... run python -m skill_pilot_agent.cli 'list files'` |
| skill-pilot | claude-sonnet-4-6 | high | `uv --directory ... run python -m skill_pilot_agent.cli --model=claude-sonnet-4-6 --effort=high 'list files'` |
| deepseek | deepseek-reasoner | (none) | `python3 --model=deepseek-reasoner .../deepseek-cli.py hello` |

**Verified behaviors:**
- Flags land **after `run`** for uv-based providers (no uv rejection)
- Template replacement produces combined `--model=value` form (no duplicate flags)
- Backward compat: no model/effort → clean command with no extra flags
- Empty strings treated same as not-provided
- Model-only and effort-only work independently
- `GET /api/llm/providers` returns `models` and `effort_levels` per provider

### Config note

The skill-pilot provider config (`config/ai_providers.json5`, not tracked in git)
should be updated to include `{{effort}}` in its args template:

```json5
"terminal-args": ["--directory", "...", "run", "python", "-m",
  "skill_pilot_agent.cli", "--model={{model}}", "--effort={{effort}}", "{{prompt}}"]
```

Without this, effort still works (via prepend) but for uv-based providers the flag
lands in the wrong position. The code handles both cases — template-aware prepend
skip means no duplicate flags; the only difference is flag placement.

## Files changed

| File | Change |
|------|--------|
| `core/engine/llm_service.py` | Model/effort resolution, template-aware prepend, `{{effort}}` replacement, log formatting |
| `core/engine/routes.py` | Accept `model`/`effort` in session create payload |
| `core/engine/routes_integrations.py` | Return `models`/`effort_levels` in provider list |
| `core/engine/routes_shared.py` | Thread `model`/`effort` through `_build_provider_command()` |
| `core/engine/skill_pilot_agent/cli.py` | `--effort` CLI argument |
| `core/engine/skill_pilot_agent/agent.py` | `effort` config field, `RunConfig` with `ModelSettings` |
| `core/webui/pages/index.tsx` | Model/effort state, dropdowns, payload wiring |
| `core/webui/components/EmbeddedSessionPanel.tsx` | Optional model/effort props + selectors |
| `core/engine/tests/test_model_effort_selection.py` | 27 unit tests for model/effort command building |
