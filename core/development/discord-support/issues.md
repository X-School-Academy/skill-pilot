# Discord Support - Review Issues

This file records all issues found during code review for the `core/development/discord-support` task.

## High

### 1) Token save/load mismatch breaks connect flow
- **Status:** Fixed
- **Issue:** `POST /api/discord/token` writes `DISCORD_BOT_TOKEN` to `config/.env`, but runtime settings load from `core/engine/.env` and cache `DISCORD_BOT_TOKEN` at import time.
- **Impact:** The "Save Token & Connect" flow does not actually make the bot connect without additional manual env setup/restart behavior.
- **References:**
  - `core/engine/routes.py:1665`
  - `core/engine/settings.py:12`
  - `core/engine/settings.py:30`
  - `core/engine/app_factory.py:10`
  - `core/engine/discord_bot.py:9`

### 2) Discord control APIs are unauthenticated
- **Status:** Fixed
- **Issue:** Broadcast and token-write endpoints are exposed without auth checks.
- **Impact:** If the service is reachable, an attacker can send mass DMs and overwrite bot credentials.
- **References:**
  - `core/engine/routes.py:1609`
  - `core/engine/routes.py:1659`
  - `core/engine/app_factory.py:18`
  - `core/engine/app_factory.py:19`

## Medium

### 3) Unsafe token write enables env injection
- **Status:** Fixed
- **Issue:** Token value is directly interpolated into `.env` content without escaping.
- **Impact:** Newline or crafted values can inject additional env variables.
- **References:**
  - `core/engine/routes.py:1662`
  - `core/engine/routes.py:1676`

### 4) Summarization guard can bypass memory budget
- **Status:** Fixed
- **Issue:** Session summarization is skipped when buffer has `<= 4` messages even if size threshold is exceeded.
- **Impact:** A few long messages can exceed intended prompt budget and hurt reliability/cost.
- **References:**
  - `core/engine/discord_session.py:65`
  - `core/engine/discord_session.py:70`
  - `core/engine/discord_bot.py:73`

## Low

### 5) Fetching inside render causes unstable UI behavior
- **Status:** Fixed
- **Issue:** Discord status/session API calls are triggered from render logic instead of effects.
- **Impact:** Potential duplicate fetches and harder-to-reason state updates.
- **References:**
  - `core/webui/pages/index.tsx:683`
  - `core/webui/pages/index.tsx:684`
  - `core/webui/pages/index.tsx:685`

### 6) Broadcast can DM same user multiple times
- **Status:** Ignored by user decision
- **Issue:** Broadcast loops through members per guild without deduplicating users across guilds.
- **Impact:** Duplicate DMs and inflated sent counters for users shared across multiple guilds.
- **References:**
  - `core/engine/discord_bot.py:85`
  - `core/engine/discord_bot.py:86`
  - `core/engine/discord_bot.py:93`
