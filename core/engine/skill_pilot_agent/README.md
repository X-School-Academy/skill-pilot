# Skill Pilot Agent

A small `openai-agents`-based CLI agent used by Skill Pilot for non-tmux
background LLM tasks. The agent talks to any OpenAI-compatible endpoint, loads
project-level instructions from `AGENTS.md` and skills under `.agent/`, and
exposes a single `bash` tool for any work that needs to inspect or change the
local filesystem.

## CLI Wrapper

The agent is invoked through:

```bash
core/bin/skill-pilot-agent "<prompt>"
```

The wrapper resolves the repo root and runs:

```bash
uv --directory core/engine run python -m skill_pilot_agent.cli "$@"
```

## Required Environment Variables

The agent uses an OpenAI-compatible HTTP API:

| Variable                | Purpose                                       |
|-------------------------|-----------------------------------------------|
| `SKILL_PILOT_BASE_URL`  | OpenAI-compatible base URL (e.g. `http://localhost:8000/v1`) |
| `SKILL_PILOT_API_KEY`   | API key sent as the OpenAI bearer token       |
| `SKILL_PILOT_MODEL`     | Default model name (overridable via `--model`) |

## CLI Arguments

| Argument           | Default            | Description                                                                 |
|--------------------|--------------------|-----------------------------------------------------------------------------|
| `--sandbox`        | `yes`              | Run inside the local sandbox profile.                                       |
| `--auto`           | `yes`              | Allow tool use without asking; `no` is parsed but not yet supported.        |
| `--network`        | `no`               | When `no`, blocks network-capable commands and applies OS-level enforcement. |
| `--model`          | `$SKILL_PILOT_MODEL` | Overrides the default model.                                              |
| `--agent-dir`      | repo root          | Working directory the agent operates in.                                    |
| `--agent-file`     | `AGENTS.md`        | Instructions file path (relative to `--agent-dir` or absolute), or `none`.  |
| `--log-level`      | `info`             | Log level for the engine logger.                                            |
| `--max-retries`    | `3`                | Retries on agent run failure.                                               |
| `--timeout`        | `60`               | Per-task timeout in seconds.                                                |
| `--bash-commands`  | all                | Comma-separated allowlist of bash executables.                              |
| `--skills-dir`     | `<agent-dir>/.agent` | Directory scanned for `SKILL.md` files.                                   |
| `--skills`         | all                | Comma-separated list of skills to load, or `none` to skip skills entirely.  |

### `--agent-file`

* Default `AGENTS.md` — loaded once from the root of `--agent-dir` (no nested files).
* Set to a relative or absolute path to point at a different instructions file.
* Set to `none` to start the agent with no project instructions file.

### `--skills`

* Default behavior loads every skill discovered under `--skills-dir`.
* A comma-separated list filters by skill name or directory name.
* `none` disables skill loading entirely.

## Provider Selection

`config/ai_providers.json5` registers a `skill-pilot` LLM provider with
`background_only: true`. Background-only providers are hidden from the WebUI
LLM dropdown. To route non-tmux background LLM calls through this agent, set:

```json5
default: {
  background_llm: 'skill-pilot',
}
```

Tmux/terminal sessions continue to use the regular `default.llm` provider.

## Examples

```bash
# Default usage
core/bin/skill-pilot-agent "Reply with OK"

# Custom model + skills
core/bin/skill-pilot-agent --model my-model --skills none "Reply with OK"

# No agent instructions file, only the prompt
core/bin/skill-pilot-agent --agent-file none "Reply with OK"

# Restricted bash allowlist, network disabled
core/bin/skill-pilot-agent \
  --bash-commands "ls,cat,pwd" \
  --network no \
  "List the README files under the current directory."
```

## Files

| File              | Purpose                                                |
|-------------------|--------------------------------------------------------|
| `cli.py`          | Argument parsing and entry point.                      |
| `agent.py`        | Builds the `openai-agents` runner and config.          |
| `agents_md.py`    | Loads the root agent instructions file.                |
| `bash_tool.py`    | Sandboxed bash function tool with command allowlists.  |
| `skills.py`       | Discovers and renders `.agent/**/SKILL.md` skills.     |
| `ignore_rules.py` | `.agentignore`-style filter for skill discovery.       |

## Logging

All modules log through `core/engine/logger.py` (`get_logger`) so the agent's
output is consistent with the rest of the engine.

## Sandbox / Network / Auto Limitations

The first release intentionally implements only default behavior for
`--sandbox`, `--auto`, and `--network`. The matrix below describes what is
actually enforced today.

### `--sandbox` (default `yes`)

* `yes` does **not** provide general process or filesystem isolation. Its only
  runtime effect is to combine with `--network no` and wrap the command in
  `sandbox-exec` on macOS.
* There is no filesystem jail, no workspace-write / read-only mode, and no
  UID / namespace isolation. The agent can still read or write anywhere the
  invoking user can.
* The working directory is pinned to `--agent-dir`, but `cd ..` and absolute
  paths are not blocked.
* `no` simply skips the macOS `sandbox-exec` wrapper.
* Linux and Windows have no OS-level sandbox at all.

### `--network` (default `no`)

`no` is enforced through two layers:

1. **Name-based deny list** in `bash_tool.py` covering common network tools
   (`curl`, `wget`, `git`, `npm`, `pip`, `uv`, `brew`, etc.). This is easy to
   bypass with anything not on the list — for example `nc`, `ssh`, `socat`,
   `dig`, `nslookup`, `ftp`, `node`, `ruby`, `perl`, `php`, or shell builtins
   such as `exec 3<>/dev/tcp/host/port`.
2. **OS-level enforcement** only on macOS via
   `sandbox-exec -p '(version 1)(allow default)(deny network*)'`.
   On Linux and Windows the bash tool fails safe and raises a `RuntimeError`
   instead of running — but **only** when `--sandbox yes`. With
   `--sandbox no --network no` the OS wrapper is skipped entirely, so only the
   name-based deny list applies.

`yes` applies no enforcement and lets commands reach the network freely.

### `--auto` (default `yes`)

* `yes` runs tools without per-call confirmation (the default `openai-agents`
  behavior).
* `no` is parsed but **not implemented**. The agent raises
  `ValueError("--auto no is parsed but not supported in the first release")`
  before running.

### Summary

| Flag             | Default works?                                | Non-default works?                       |
|------------------|------------------------------------------------|------------------------------------------|
| `--sandbox yes`  | Partial (macOS-only, network-coupled)          | `no` works; `yes` is still weak          |
| `--network no`   | macOS strict; Linux / Windows refuse to run    | `yes` ungated                            |
| `--auto yes`     | Yes                                            | `no` raises immediately                  |

A future release should add Linux `bwrap` / `firejail`, a real filesystem
jail, a network namespace, a broader process-level deny list, and a true
`--auto no` confirmation flow.
