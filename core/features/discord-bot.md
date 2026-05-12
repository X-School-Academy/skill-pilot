# Feature Retrieval Index: Discord Bot Integration

## Retrieval Keywords

Discord, discord bot, discord session, discord broadcast, discord status, discord sessions, discord_bot, discord_session, create-discord-bot, discord channel, discord integration, Discord API, bot token, channel_id

## Scope

- Discord bot creation and management
- Broadcasting messages via Discord
- Listing active Discord sessions and channels
- Discord status check
- Excludes: general chat/LLM (separate feature)

## Main Behavior

- `POST /api/discord/broadcast` sends a message to a Discord channel
- `GET /api/discord/status` returns bot connection status
- `GET /api/discord/sessions` lists active Discord sessions
- `GET /api/discord/sessions/{channel_id}` returns a specific session
- Discord bot runs as a background service managed via tmux or direct process

## Code Map

- `core/engine/routes_integrations.py` — `/api/discord/*` route handlers
- `core/engine/discord_bot.py` — Discord bot logic
- `core/engine/discord_session.py` — Discord session management
- `core/skills/system/create-discord-bot/` — skill for creating and configuring discord bots

## Search Commands

```bash
rg "api/discord" core/engine/routes_integrations.py -n
cat core/engine/discord_bot.py | head -40
find core/skills/system/create-discord-bot/ -type f
```

## Related Features

- `core/features/llm-ai-chat.md`
- `core/features/skill-agent-system.md`

## Update Notes

- Discord bot token must be set in `config/.env`
- Sessions identified by Discord `channel_id`
- Bot requires `discord.py` or equivalent in Python dependencies
