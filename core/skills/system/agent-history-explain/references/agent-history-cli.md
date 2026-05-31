# `core/bin/agent-history` — CLI Reference

Tool that converts a recorded agent session (`.jsonl`) into a human-readable markdown transcript.

## Usage

```
./core/bin/agent-history <target>
```

- **`<target>`** — a session reference. Accepted forms:
  - Path relative to the repo root (e.g. `.skillpilot/agent-sessions/20260521T021318Z-codex-019e47da-9544-7fe0-87af-51703eaa850f.jsonl`)
  - File name only (e.g. `20260521T021318Z-codex-019e47da-9544-7fe0-87af-51703eaa850f.jsonl`)
  - Session id substring (e.g. `019e47da` or `20260521T021318Z`) — the CLI resolves it under `.skillpilot/agent-sessions/`

The CLI prints the markdown transcript to **stdout**. It does **not** write a file. To save it, redirect stdout.

## Options

- `-h`, `--help` — show usage.

(There are no other flags. Do not pass `--output`, `--format`, etc. — they do not exist.)

## Where session files live

`.skillpilot/agent-sessions/` at the repo root. Files are named:

```
<UTC-timestamp>-<agent>-<session-id>.jsonl
```

Example:

```
20260521T234205Z-claude-b7554d5c-9754-496c-847d-17bc5070ecd7.jsonl
```

Supported agents seen in this project: `codex`, `claude`, `gemini`, `opencode` (more may be added).

## Output format

The exported markdown starts with a header like:

```markdown
# Agent history

This session was recorded against a specific git commit. To reproduce the work, check out that commit and replay the user prompts below:

    git checkout <commit>

- commit: <sha>
- agent: <agent-name>
- model: <model-id>
```

Then it alternates:

```markdown
## user_prompt

<the user's instruction, verbatim>

## agent_response

<the agent's reply, including its plan, role announcements, and natural-language responses>
```

Notes:

- Tool calls and tool outputs may be inlined inside `agent_response` blocks (as code fences or quoted text), depending on the agent.
- Anything inside backticks or fenced code blocks is **content**, not commentary — do not edit it when post-processing.

## Typical recipes

### Save an export to a file

```
./core/bin/agent-history 019e47da > /tmp/session.md
```

### Save under a custom destination path

```
./core/bin/agent-history 20260521T234205Z-claude-b7554d5c > workspace/agent-history/claude-session.md
```

### Resolve an ambiguous reference first

If a short id substring matches multiple session files in `.skillpilot/agent-sessions/`, the CLI will fail or pick one arbitrarily. To be safe, list files first:

```
ls .skillpilot/agent-sessions/ | grep <substring>
```

Then pass the full file name.

## How this skill uses the CLI

1. Locate the session file in `.skillpilot/agent-sessions/` (see Step 1 of `SKILL.md`).
2. Run `./core/bin/agent-history <resolved-reference>` and redirect stdout into `<destination>/<base>.md`.
3. Verify the resulting file exists and is non-empty.
4. Apply the user-prompt-only spelling/grammar pass (Step 3 of `SKILL.md`).
