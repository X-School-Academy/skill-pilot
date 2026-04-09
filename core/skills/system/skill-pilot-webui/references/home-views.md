# Home Views

These views live inside the main `/` WebUI shell and usually keep the left navigation visible.

## General Pattern

1. Open the base URL from `get_webui_url`
2. Navigate to the target query-string view
3. Wait for the visible header, panel, or list to settle
4. Snapshot before interacting

## Supported Embedded Views

### New Session

- Route: `/`
- Use for starting a prompt-driven agent session or workflow-backed new session
- Typical actions:
  - fill the main prompt
  - choose provider when relevant
  - toggle sandbox, auto, network, native terminal, or workflow trigger controls
  - start the session and observe the terminal area

### Processes

- Route: `/?view=processes`
- Use for read-only inspection of tmux-backed sessions and opening terminal views for running sessions
- Typical actions:
  - inspect system and user sessions
  - open readonly terminal tabs
  - verify long-running tasks

### Discord Bot

- Route: `/?view=discord-bot`
- Use for bot status, sessions, and token-related UI flows

### Skills

- Route: `/?view=skills`
- Use for skill browsing and skill enable or disable actions

### MCP Servers

- Route: `/?view=mcp-servers`
- Use for MCP server inspection, configuration edits, sync actions, and test runs

### Schedules

- Route: `/?view=schedule`
- Use for creating or editing schedules and verifying cron-like timing previews

### Extensions

- Route: `/?view=extensions`
- Use for extension browsing or configuration inspection

### AI & Security

- Route: `/?view=ai-security`
- Use for security flags, new-session defaults, and env safe-guard related settings

### Profile

- Route: `/?view=profile`
- Use for editing visible profile fields such as name, location, school, and timezone

## Browser Guidance

- Re-snapshot after switching embedded views because the content changes without a full hard navigation
- Prefer visible text labels from the active panel over assuming the current view from the URL alone
