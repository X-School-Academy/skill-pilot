# Discord Bot

## Brief

Frozen core Discord integration that connects a bot token, stores channel conversation memory, and exposes session history and broadcast support in the current implementation.

## User Value

- Brings Discord-based agent conversations into the Skill Pilot UI.
- Supports both setup and ongoing channel/session monitoring.
- Makes cached conversation history accessible by channel.
- Freezes the current behavior so humans and AI agents can reason about the live Discord integration without re-reading the whole codebase.

## Main Behavior

- Checks Discord auth state and token availability before loading the main view.
- Saves the bot token through the WebUI.
- Lists Discord sessions by channel and loads message history for the active tab.
- Shows connection status, guild count, and auth-related errors.
- Supports server-side broadcast operations and cached session retrieval.
- Supports only one human user in a whole Discord server for reliable conversation context.
- Treats one Discord channel as one session, so all human messages in that channel are interpreted as one logical user context.
- Fits direct-message usage best; shared multi-user guild channels are outside the supported conversation model.
- Stores full conversation history as append-only JSONL under `.skillpilot/discord/sessions/`, keyed by `channel_id`.
- Uses three memory tiers: complete cached history, active live buffer after the last summary, and retained memory summary from earlier turns.
- Keeps the most recent `DISCORD_BUFFER_MSG_COUNT` messages in the live buffer for active context.
- On reload, compacts overflowed unsummarized messages into retained memory before trimming the live buffer so restart does not silently drop context.
- Triggers normal summarization from the configured context budget derived from `DISCORD_MAX_BUFFER_TOKENS`.
- Injects retained memory into the LLM as assistant-authored memory context rather than a system instruction.
- Exposes full cached history in the WebUI for session inspection and support review.

## Related Features

- `processes.md`
- `ai-and-security.md`
- `profile.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/discord_bot.py`
- `core/engine/discord_session.py`
- `core/engine/routes.py`
- Functions and classes: `fetchDiscordAuthStatus`, `fetchDiscordStatus`, `fetchDiscordSessions`, `fetchDiscordHistory`, `saveDiscordToken`, `ChatSession`, `SessionManager`, `get_llm_messages`, `load_from_cache`, `summarise`
- Keywords: `discordActiveTab`, `DISCORD_BUFFER_MSG_COUNT`, `DISCORD_MAX_BUFFER_TOKENS`, `.skillpilot/discord/sessions`
- API routes: `/api/discord/status`, `/api/discord/sessions`, `/api/discord/sessions/{channel_id}`, `/api/discord/token`, `/api/discord/broadcast`
