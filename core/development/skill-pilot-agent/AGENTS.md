# Skill Pilot Agent Feature Instructions

## Scope

These instructions apply to documentation and future changes for the Skill Pilot background agent feature.

Primary implementation files:

- `core/bin/skill-pilot-agent`
- `core/engine/skill_pilot_agent/`
- `core/engine/llm_service.py`
- `config/ai_providers.json5`
- `core/engine/tests/test_skill_pilot_agent_cli.py`

## Maintenance Rules

- Keep `requirements.md` aligned with the implemented behavior, not only the original request.
- Keep `implementation.md` focused on code design, control flow, and limitations.
- Preserve the separation between background LLM provider selection and normal/tmux LLM provider selection.
- Do not make `skill-pilot` a visible normal LLM provider unless the product decision explicitly changes.
- Treat `--sandbox`, `--network`, and `--auto` claims carefully. Document what is actually enforced.
- Respect ignore files when adding skill discovery behavior or documentation.
- Add or update tests when changing CLI arguments, provider selection, bash restrictions, or instruction loading.

## Review Checklist

- Does `default.background_llm` remain the only automatic selector for the Skill Pilot provider?
- Are terminal/tmux sessions unaffected?
- Does the CLI still fail clearly for missing endpoint configuration?
- Does the agent still expose only bash tooling?
- Are security limitations stated plainly in docs?
- Are tests updated for changed behavior?
