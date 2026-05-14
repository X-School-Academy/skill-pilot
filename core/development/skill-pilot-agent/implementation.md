# Skill Pilot Agent Implementation

The feature is implemented as a CLI-backed background LLM provider. The main design decision is to keep normal LLM provider selection unchanged while adding a separate background provider path that can opt into the Skill Pilot agent.

## Control Flow

1. `llm_get_text`, `llm_get_json`, and `llm_stream` call `get_background_provider()` when no explicit provider is supplied.
2. `get_default_background_llm_provider_id()` reads `default.background_llm`.
3. Only the exact value `skill-pilot` activates the Skill Pilot background provider.
4. The provider config builds a command using `core/bin/skill-pilot-agent`.
5. The wrapper runs `uv --directory core/engine run python -m skill_pilot_agent.cli`.
6. The CLI resolves paths, model config, endpoint environment, and runtime flags.
7. `agent.py` builds an `openai-agents` `Agent` with an `OpenAIChatCompletionsModel`.
8. The agent receives composed instructions from built-in behavior rules, the configured root agent file, and selected skills.
9. The only available tool is `bash`.
10. The CLI prints final output to stdout or prints errors to stderr with exit code `1`.

## Provider Integration

`config/ai_providers.json5` contains:

- `default.background_llm: 'skill-pilot'`
- an LLM provider with `id: 'skill-pilot'`
- `bin: 'core/bin/skill-pilot-agent'`
- `background_only: true`
- sandbox, auto, network, model, prompt, and endpoint env arguments

`core/engine/llm_service.py` hides background-only providers from normal provider lists unless background resolution explicitly includes them.

## Agent Package

`core/engine/skill_pilot_agent/cli.py` owns:

- argument parsing
- `yes|no` coercion
- prompt validation
- root path resolution
- `--agent-file none`
- construction of `SkillPilotAgentConfig`
- exit-code handling

`core/engine/skill_pilot_agent/agent.py` owns:

- required endpoint validation
- model/client setup
- instruction composition
- bash tool registration
- retry behavior
- filesystem-task guard that requires bash usage

`core/engine/skill_pilot_agent/bash_tool.py` owns:

- executable allowlist parsing
- network command deny list
- macOS `sandbox-exec` network denial
- command execution from `--agent-dir`
- formatted bash output

`core/engine/skill_pilot_agent/agents_md.py` owns root instruction loading. It intentionally does not recurse.

`core/engine/skill_pilot_agent/skills.py` owns skill discovery and instruction rendering.

`core/engine/skill_pilot_agent/ignore_rules.py` owns ignore-file parsing for skill discovery.

## Safety Model

The current safety model is intentionally narrow:

- no general filesystem sandbox
- no complete process sandbox
- no cross-platform network namespace
- macOS-only strict network denial through `sandbox-exec`
- command-name deny list for common network tools
- fail-safe behavior when strict network denial is requested but unavailable
- unsupported `--auto no` mode fails before running the agent

## Verification Surface

Focused tests currently cover:

- CLI defaults
- `--agent-file none`
- `--skills none`
- invalid `yes|no` values
- bash command allowlist enforcement
- bash execution from the configured directory
- filesystem prompts requiring bash
- root-only `AGENTS.md` loading
- custom agent file loading
- selected skill loading

Recommended future coverage:

- background provider selection in `llm_service.py`
- fallback behavior when `background_llm` is absent or invalid
- explicit provider override behavior
- provider environment expansion for Skill Pilot endpoint variables
