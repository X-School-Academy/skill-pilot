# Discord Bot

## Brief

Discord integration that connects a bot token, lists channel sessions, and exposes message history and broadcast support.

## User Value

- Brings Discord-based agent conversations into the Skill Pilot UI.
- Supports both setup and ongoing channel/session monitoring.
- Makes cached conversation history accessible by channel.

## Main Behavior

- Checks Discord auth state and token availability before loading the main view.
- Saves the bot token through the WebUI.
- Lists Discord sessions by channel and loads message history for the active tab.
- Shows connection status, guild count, and auth-related errors.
- Supports server-side broadcast operations and cached session retrieval.

## Related Features

- `processes.md`
- `ai-and-security.md`
- `profile.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/discord_bot.py`
- `core/engine/discord_session.py`
- `core/engine/routes.py`
- Keywords: `fetchDiscordAuthStatus`, `fetchDiscordStatus`, `fetchDiscordSessions`, `fetchDiscordHistory`, `saveDiscordToken`, `discordActiveTab`
- API routes: `/api/discord/status`, `/api/discord/sessions`, `/api/discord/sessions/{channel_id}`, `/api/discord/token`, `/api/discord/broadcast`

