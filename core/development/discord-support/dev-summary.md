# Discord Support — Dev Summary

## What Was Done

### Step 1: Added py-cord dependency
- Added `py-cord==2.6.1` to `core/engine/pyproject.toml`

### Step 2: Added Discord settings
- Added `DISCORD_BOT_TOKEN`, `DISCORD_SESSIONS_DIR`, `DISCORD_MAX_BUFFER_TOKENS`, `DISCORD_BUFFER_MSG_COUNT` to `core/engine/settings.py`
- All configurable via environment variables with sensible defaults

### Step 3: Created three-tier memory session manager
- **`core/engine/discord_session.py`** — new file
- `ChatSession` class manages per-channel memory with three tiers:
  - **Tier 1 (Running Summary)**: condensed summary of older history, stored as first line in JSONL
  - **Tier 2 (Recent Buffer)**: last 20 messages verbatim in memory
  - **Tier 3 (Full Cache)**: complete JSONL file on disk at `.skillpilot/discord/sessions/{channel_id}.jsonl`
- `SessionManager` class manages all sessions, loads from cache on startup
- Summarisation triggers when total chars exceed 75% of budget (~36K chars / ~12K tokens)
- Uses `llm_get_text()` to generate summaries — no extra dependency needed
- Token budget: 16K tokens (~48K chars) — research-backed sweet spot

### Step 4: Created Discord bot module
- **`core/engine/discord_bot.py`** — new file
- Uses py-cord with message_content + members intents
- Handles ALL text channels and DMs (as confirmed)
- System prompt: "You are an AI personal assistant to help user to do any work on behalf of the user."
- Calls `llm_get_text()` via `asyncio.to_thread()` for non-blocking LLM responses
- Shows typing indicator while waiting for LLM
- Splits long replies into 2000-char chunks (Discord limit)
- `send_dm_to_all()` function for broadcasting to all guild members

### Step 5: Integrated with FastAPI lifecycle
- Discord bot starts as `asyncio.create_task()` during FastAPI startup in `app_factory.py`
- Graceful shutdown via `bot.close()` during FastAPI shutdown
- Only activates if `DISCORD_BOT_TOKEN` is set

### Step 6: Added broadcast endpoint
- `POST /api/discord/broadcast` in `core/engine/routes.py`
- Accepts `{"message": "text"}` and sends DM to all guild members
- Returns `{"status": "ok", "sent_count": N}`

## Files Changed

| File | Action | Description |
|---|---|---|
| `core/engine/pyproject.toml` | Edited | Added `py-cord==2.6.1` dependency |
| `core/engine/settings.py` | Edited | Added Discord bot settings (token, sessions dir, buffer limits) |
| `core/engine/discord_session.py` | **Created** | Three-tier memory session manager (ChatSession + SessionManager) |
| `core/engine/discord_bot.py` | **Created** | Discord bot with LLM-powered auto-reply |
| `core/engine/app_factory.py` | Edited | Start/stop Discord bot on server lifecycle |
| `core/engine/routes.py` | Edited | Added `POST /api/discord/broadcast` endpoint |
| `core/engine/routes.py` | Edited | Added Discord status, sessions, and token endpoints |
| `core/webui/pages/index.tsx` | Edited | Renamed Remote Clients to Discord Bot, added token setup + session history view |

### Step 7: Added Discord API endpoints for WebUI
- `GET /api/discord/status` — returns `has_token`, `connected`, `bot_name`, `guild_count`
- `GET /api/discord/sessions` — lists all sessions with metadata via `SessionManager.list_sessions()`
- `GET /api/discord/sessions/{channel_id}` — returns full JSONL history via `ChatSession.get_full_history()`
- `POST /api/discord/token` — reads `config/.env`, updates or appends `DISCORD_BOT_TOKEN`, writes back, reloads into `settings.DISCORD_BOT_TOKEN`

### Step 8: Updated WebUI — Discord Bot page
- Renamed `ActiveView` type from `'remote-clients'` to `'discord-bot'`
- Changed nav item to "Discord Bot" with `IconBrandDiscord`
- Added token setup form: text input + "Save & Connect" button (shown when no token is configured)
- Added status bar showing bot name and guild count when connected
- Added vertical session tabs listing all Discord sessions by channel ID
- Added message history panel with colour-coded entries (blue for user, green for assistant, grey for system/summary)
- Auto-fetches status and sessions on view mount; refreshes after saving token

## Design Decisions Confirmed

1. **System prompt**: "You are an AI personal assistant to help user to do any work on behalf of the user."
2. **Channel scope**: All text channels + DMs
3. **Concurrency**: `asyncio.to_thread()` for parallel LLM calls
4. **Token budget**: 16K tokens (~48K chars) — optimal recall-to-cost ratio
5. **Memory architecture**: Three-tier (running summary + recent buffer + JSONL cache)
