Refer to `/Users/frankhe/myworks/jit-app-service-mcp/src/discord_bot.py` using "py-cord==2.6.1", with os.getenv('DISCORD_BOT_TOKEN')

## Discord Bot

1. Create a Discord bot in the backend core engine.
2. The bot will auto-reply to any incoming message in a related text channel or DM channel.
3. The bot can send an initial message to a DM channel (if more than one Discord member is connected to the bot, it will send the message to all members).

## Session Management

4. For each Discord server's text channel or DM channel, create a `session` to persist the state of chat messages by Discord channel ID.
5. Only when we receive a text message from a channel will we create the session.
6. Once we receive a message from a DM or server channel, we will use the default LLM provider to respond to the user by agent CLI in JSON format — refer to `config/ai_providers.json5`.

## Three-Tier Memory Architecture

The chat memory uses three tiers to balance recall quality, token cost, and crash recovery:

### Tier 1: Running Summary (~2K tokens, stable prefix)

- A condensed summary of all older conversation history, capturing key facts, user preferences, and important decisions.
- Always placed at the beginning of the LLM prompt to maximise prompt cache hits (cached prefix stays stable across turns).
- Updated each time older messages are summarised out of the recent buffer.
- Stored as the first line in the JSONL file: `{role: "system", type: "summary", message: str}`.

### Tier 2: Recent Buffer (last 20 messages verbatim, ~8–12K tokens)

- The most recent messages kept word-for-word in memory for full conversational detail.
- Sent to the LLM after the running summary on every request.
- When the recent buffer exceeds ~12K tokens (~36K characters), the oldest half of the buffer is summarised by the LLM and merged into the running summary (Tier 1).

### Tier 3: Full History Cache (JSONL file on disk, unlimited)

- Complete conversation record saved to `.skillpilot/discord/sessions/{channel_id}.jsonl`.
- Each line is a JSON object: `{role: "user"|"assistant"|"system", message: str}`.
- Both user messages and assistant replies are appended after each exchange.
- Used for crash recovery — on restart, reload the running summary and recent buffer from this file.

## Memory Budget

- **Total LLM input budget**: ~16K tokens (~48K characters) for summary + recent buffer combined. This is the research-backed sweet spot — best recall-to-cost ratio, avoids the "lost-in-the-middle" degradation that occurs past 32K tokens.
- **Summarisation trigger**: When the total live session (summary + buffer) exceeds 16K tokens, summarise the oldest messages in the buffer and merge into the running summary, then flush the full history to cache and reload — same as a service restart.

## Crash Recovery

- Each time the bot crashes or restarts, reload the chat session from the JSONL cache file, reconstructing the running summary and recent buffer.

## WebUI

- In the left navigation menu, replace "Remote Clients" with "Discord Bot" using a Discord icon.
- If `DISCORD_BOT_TOKEN` is not configured, show a token input field and a "Connect" button that saves the token to `config/.env` and triggers a bot connection.
- If the bot is connected, show a status bar with the bot name and guild count.
- Display all Discord sessions as vertical tabs (by channel ID), with the active tab showing the full message history from the JSONL cache.
- Message history entries are colour-coded by role: user messages, assistant replies, and system/summary entries each have a distinct style.
- Backend API endpoints:
  - `GET /api/discord/status` — returns bot connection status, name, and guild count.
  - `GET /api/discord/sessions` — lists all sessions with metadata (channel ID, message count, buffer size, has summary).
  - `GET /api/discord/sessions/{channel_id}` — returns the full JSONL history for a channel.
  - `POST /api/discord/token` — saves the Discord bot token to `config/.env` and returns the updated status.
