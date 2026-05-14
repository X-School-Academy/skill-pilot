# Feature Retrieval Index: Skill Agent System

## Retrieval Keywords

skill agent, skill-agent, skill install, skill-install, skill eval, skill-eval, skill verify, skill-verify, use-skill-agent, agent skill, skill runner, skill execution, SKILL.md, skill category, system skill, user skill, mcp_to_skills, skill service, skill install from git, install-third-party-agent-skill-from-git, skill_pilot_agent, skills.py, agents_md.py, bash_tool.py, ignore_rules, cli.py

## Scope

- Skill definition format (`SKILL.md`) and discovery
- Skill execution via the skill-agent CLI
- Skill installation from git or local sources
- Skill evaluation and verification
- MCP-to-skills bridge for AI agent tool access
- Excludes: workflow execution (separate), config/MCP management (separate)

## Main Behavior

- `core/bin/skill-agent` runs a skill by category/name with an agent
- `core/bin/skill-install` installs a skill from git
- `core/bin/skill-eval` evaluates a skill's output
- `core/bin/skill-verify` verifies a skill definition
- `core/engine/mcp_servers/mcp_to_skills/service.py` exposes skills as MCP tools
- Skills discovered under `core/skills/system/`, `core/skills/user/`, `dev-swarm/skills/`
- Each skill has a `SKILL.md` with name, description, and instructions

## Code Map

- `core/bin/skill-agent` — skill runner CLI
- `core/bin/skill-install` — skill installer CLI
- `core/bin/skill-eval` — skill evaluator CLI
- `core/bin/skill-verify` — skill verifier CLI
- `core/engine/skill_pilot_agent/` — agent core: `agent.py`, `agents_md.py`, `bash_tool.py`, `cli.py`, `ignore_rules.py`, `skills.py`
- `core/engine/mcp_servers/mcp_to_skills/` — MCP bridge: `service.py`, `install.py`, `eval.py`, `sync.py`, `verify.py`, `cli.py`, `run_workflow.py`, `workflow_execution.py`
- `core/skills/system/` — system skills directory
- `core/skills/user/` — user skills directory
- `dev-swarm/skills/` — dev swarm skills directory
- `core/skills/system/background-prompt/` — background-prompt skill
- `core/skills/system/install-third-party-agent-skill-from-git/` — git skill installer skill

## Search Commands

```bash
find core/skills/system/ -name "SKILL.md" | head -20
find core/skills/user/ -name "SKILL.md" 2>/dev/null | head -10
rg "SKILL.md" core/engine/skill_pilot_agent/skills.py -n
cat core/engine/skill_pilot_agent/agent.py | head -40
find core/engine/mcp_servers/mcp_to_skills/ -type f
```

## Related Features

- `core/features/config-settings-mcp-skills.md`
- `core/features/workflow-runner-editor.md`
- `core/features/mcp-terminal-server.md`

## Update Notes

- Skill names are derived from the `SKILL.md` `name:` frontmatter field
- `.agentignore`, `.claudeignore`, `.geminiignore`, `.codexignore` must be respected by the agent
- `ignore_rules.py` enforces ignore file rules; never bypass
- Skills in `core/skills/user/` are user-managed; do not overwrite on upgrade
