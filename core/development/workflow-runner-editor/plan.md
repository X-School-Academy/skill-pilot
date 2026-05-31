# Workflow Runner and Editor Development Plan

## Current State

The workflow runner/editor feature is implemented and reverse-engineered into this feature folder.

Completed behavior:

- Web UI workflow editor persists `data.subagent`.
- Workflow validation accepts current agent-node schema.
- Agent-workflow skill docs use subagent terminology.
- Tmux workflow monitor supports `auto_continue` and `start_by_prompt`.
- Existing tmux session workflow mode can auto-detect `TMUX_SESSION_NAME`.
- Background mode can be forced with `--tmux-session=none`.
- Sample user subagents and sample workflow exist for smoke testing.
- Frozen retrieval index exists at `core/features/workflow-runner-editor.md`.

## Development Principles

- Keep workflow JSON schema stable: `type: "agent"` plus `data.subagent`.
- Avoid compatibility code for removed skill-based workflow nodes unless explicitly reintroduced as a product requirement.
- Keep node prompts scoped to the current node.
- Keep workflow file paths as runtime arguments and metadata, not node prompt content.
- Preserve the distinction between tmux monitor mode and non-tmux background mode.
- Preserve the human-in-the-loop contract for `start_by_prompt`.

## High-Priority Follow-Up Items

1. Update CLI help text for `--tmux-session`.
   - Current behavior auto-detects `TMUX_SESSION_NAME` when omitted.
   - Help text should say omit to auto-detect and use `none` to force background mode.

2. Add an explicit background-mode affordance if needed.
   - Possible CLI flag: `--background` or `--no-tmux`.
   - Must remain equivalent to `--tmux-session=none`.

3. Strengthen background-provider checks.
   - Non-tmux workflow execution requires a provider capable of writing local output files.
   - Consider a clear warning or preflight when the selected background provider is unlikely to write files.

4. Keep sample workflow reliable.
   - Maintain `core/workflows/user-subagent-test-workflow.json`.
   - Maintain the four `core/subagents/user/workflow-*.md` subagents.
   - Keep expected output behavior simple and deterministic enough for smoke testing.

## Test Plan

Run after workflow code or docs change:

```bash
uv --directory core/engine run pytest tests/test_run_workflow_cli.py tests/test_subagent_install.py
```

Run after prompt or background execution changes:

```bash
core/bin/run-workflow --tmux-session=none core/workflows/user-subagent-test-workflow.json "Run the user subagent test workflow."
```

Run after Web UI workflow editor changes:

```bash
core/webui/node_modules/.bin/tsc --noEmit --project core/webui/tsconfig.json
core/webui/node_modules/.bin/eslint core/webui/pages/workflows/index.tsx
```

## Review Checklist

- Does Web UI still save `data.subagent`?
- Does workflow validation still require `subagent` or `responsibility`?
- Does `start_by_prompt` still preserve `previous_provider` until next node launch?
- Does `continue-workflow-action` skip confirmation when the user explicitly approved continuation?
- Does `--tmux-session=none` still force background mode from inside tmux?
- Do node prompts avoid `Workflow file:`?
- Do tests cover mode selection and prompt invariants?

