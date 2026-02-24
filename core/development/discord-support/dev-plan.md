# Discord Support — Dev Plan

## Gap Analysis

| Requirement | Current State | Gap |
|---|---|---|
| Discord bot in core engine | No Discord code exists in `core/engine/` | New module needed |
| py-cord dependency | Not in `pyproject.toml` | Must add `py-cord==2.6.1` |
| Auto-reply via LLM | `llm_service.py` has `llm_get_text()` for CLI-based LLM calls | Can reuse directly |
| Session persistence (JSONL) | No session/storage module exists | New module needed |
| Three-tier memory | No memory management exists | New module needed |
| Bot token from env | `.env` pattern already used in `settings.py` | Add `DISCORD_BOT_TOKEN` to settings |
| Run alongside FastAPI | `app_factory.py` manages startup/shutdown events | Start bot as background asyncio task |

## Architecture Decision

The Discord bot will run **in the same process** as the FastAPI server, started as a background `asyncio.create_task()` during FastAPI's startup event. This avoids managing a separate process and allows the bot to directly import and call `llm_get_text()`.

## Implementation Steps

### Step 1: Add dependency

**File:** `core/engine/pyproject.toml`

Add `py-cord==2.6.1` to the dependencies list.

### Step 2: Add settings

**File:** `core/engine/settings.py`

Add:
- `DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")` — bot token from env
- `DISCORD_SESSIONS_DIR` — path to `.skillpilot/discord/sessions/` under `PROJECT_DIR`
- `DISCORD_MAX_BUFFER_TOKENS = int(os.getenv("DISCORD_MAX_BUFFER_TOKENS", "16384"))` — the 16K token budget
- `DISCORD_BUFFER_MSG_COUNT = int(os.getenv("DISCORD_BUFFER_MSG_COUNT", "20"))` — recent buffer size

### Step 3: Create session manager

**New file:** `core/engine/discord_session.py`

The `ChatSession` class manages one channel's three-tier memory:

```
class ChatSession:
    channel_id: str
    summary: str              # Tier 1: running summary
    buffer: list[dict]        # Tier 2: recent messages [{role, message}]
    _total_chars: int         # tracked for threshold checks

    def __init__(channel_id, sessions_dir)
    def add_message(role, message)     # append to buffer + JSONL file
    def get_llm_messages() -> list     # return [summary_msg, *buffer] for LLM
    def _check_and_summarise(llm_fn)   # if over budget, summarise oldest half
    def _flush_to_cache()              # write full state to JSONL
    def _load_from_cache()             # reconstruct from JSONL on restart

class SessionManager:
    sessions: dict[str, ChatSession]

    def get_or_create(channel_id) -> ChatSession
    def load_all()                     # scan sessions dir on startup
```

**Key details:**
- Token counting: approximate at ~3 chars per token (industry standard for English text)
- Summary stored as first line in JSONL: `{"role": "system", "type": "summary", "message": "..."}`
- Regular messages: `{"role": "user"|"assistant", "message": "..."}`
- Summarisation uses `llm_get_text()` with a system prompt asking for condensed key facts
- When buffer exceeds ~12K tokens (~36K chars), oldest half is summarised into Tier 1
- Total budget check: summary + buffer must stay under 16K tokens (~48K chars)

### Step 4: Create Discord bot module

**New file:** `core/engine/discord_bot.py`

Reference: `/Users/frankhe/myworks/jit-app-service-mcp/src/discord_bot.py`

```python
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # Log bot is online
    # Load existing sessions from cache via SessionManager

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Get or create session by channel_id
    # Add user message to session
    # Build LLM messages (summary + buffer)
    # Call llm_get_text() in a thread (it's blocking/subprocess)
    # Add assistant reply to session
    # Send reply to Discord channel

async def send_dm_to_all(text):
    # Iterate all guilds, all members, send DM
    # Used for broadcast initial messages (requirement #3)

async def start_bot():
    # bot.start(token) — non-blocking coroutine
```

**Key details:**
- `on_message` handles both DM and server text channels
- Uses `asyncio.to_thread(llm_get_text, messages)` since `llm_get_text` is synchronous (subprocess)
- Shows typing indicator while waiting for LLM response
- Discord has a 2000-char message limit — split long replies into multiple messages

### Step 5: Integrate with FastAPI startup

**File:** `core/engine/app_factory.py`

In the existing `_startup_mcp_bridge()` event handler, add:

```python
# Start Discord bot if token is configured
from settings import DISCORD_BOT_TOKEN
if DISCORD_BOT_TOKEN:
    from discord_bot import start_bot
    asyncio.create_task(start_bot())
    logger.info("Discord bot started")
```

In the existing `_shutdown_mcp_bridge()` event handler, add:

```python
# Stop Discord bot gracefully
if DISCORD_BOT_TOKEN:
    from discord_bot import bot
    await bot.close()
    logger.info("Discord bot stopped")
```

### Step 6: Add API endpoint for broadcast DM

**File:** `core/engine/routes.py`

Add a REST endpoint to trigger the broadcast DM feature (requirement #3):

```python
@router.post("/api/discord/broadcast")
async def discord_broadcast(request: Request):
    data = await request.json()
    message_text = data.get("message", "").strip()
    if not message_text:
        return JSONResponse(status_code=400, content={"error": "message is required"})
    from discord_bot import send_dm_to_all
    count = await send_dm_to_all(message_text)
    return {"status": "ok", "sent_count": count}
```

## Open Questions

1. **System prompt**: What system prompt should the bot use when talking to Discord users? Should it identify itself with a name/personality, or use a generic assistant prompt? (Default: use `build_chat_system_message()` from `llm_service.py`)

System prompt: You are an AI personal assistant to help user to do any work on behalf of the user. 

2. **Which channels to respond in**: Should the bot respond in ALL text channels, or only specific ones? The reference bot has channel-specific logic. (Default from requirement: all channels + DMs)

ALl.

3. **LLM provider mode**: The current `llm_get_text()` runs CLI tools synchronously. For a Discord bot handling multiple users, this means one LLM call at a time per thread. Is this acceptable, or should we add concurrency? (Default: use `asyncio.to_thread()` which allows multiple concurrent calls)

Yes

## Files Changed Summary

| File | Action | Description |
|---|---|---|
| `core/engine/pyproject.toml` | Edit | Add py-cord dependency |
| `core/engine/settings.py` | Edit | Add Discord-related settings |
| `core/engine/discord_session.py` | **New** | Session manager with three-tier memory |
| `core/engine/discord_bot.py` | **New** | Discord bot with message handling |
| `core/engine/app_factory.py` | Edit | Start/stop bot on server lifecycle |
| `core/engine/routes.py` | Edit | Add broadcast DM endpoint |
