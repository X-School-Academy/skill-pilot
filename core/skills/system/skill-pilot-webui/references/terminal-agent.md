# Direct Agent Terminal

Use the direct terminal page to show an agent-backed terminal session without the left nav shell.

## Purpose

- Demo how an AI agent behaves inside a live terminal session
- Capture a clean browser view for screenshots or screen recordings
- Open an existing agent session without submitting a new prompt

## Current Route Model

The current WebUI implementation opens direct terminal views by tmux session name:

```text
/terminal?session=<session-name>
```

There is no separate browser route that accepts a distinct `agent_id` parameter in the current implementation. In practice, the agent terminal is opened by the session identifier that backs that agent run.

## How To Open By Agent Identifier

If the user says "agent id", resolve it to the tmux session name used by the live session:

1. Inspect the current context for the session name
2. If unknown, open `/terminals` or `/?view=processes` and identify the matching live session
3. Open the direct terminal route:

```text
/terminal?session=<resolved-session-name>
```

### Readonly variant

```text
/terminal?session=<resolved-session-name>&readonly=1
```

## Notes

- This route shows the terminal content without the left nav
- It is suitable for demos, recordings, and education flows
- Once open, the agent can continue interacting with the same tmux-backed session while the browser view is captured

## History View

For static review of terminal output history, use:

```text
/terminal/history?session=<resolved-session-name>
```
