# Workflow Runner and Editor Changelog

## 2026-05-23

- Created reverse-engineered codeware development docs for the workflow runner/editor feature.
- Captured current workflow requirements, implementation notes, maintenance rules, and development plan.
- Documented the subagent workflow schema: runnable nodes remain `type: "agent"` and use `data.subagent`.
- Documented tmux and background execution modes:
  - managed Web UI tmux mode
  - existing tmux session mode through `TMUX_SESSION_NAME`
  - forced non-tmux mode through `--tmux-session=none`
- Documented `auto_continue` and `start_by_prompt` behavior.
- Recorded the prompt-scope invariant: node agents must not receive the workflow JSON file path.
- Recorded background smoke test result for `core/workflows/user-subagent-test-workflow.json`.

