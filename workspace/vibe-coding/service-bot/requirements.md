
Create a Discord bot that can talk to Discord users by direct private message.

Refer to the root of the Skill Pilot project for how to use the AI Agent CLI as an LLM provider and how to write a Discord bot in Python.

It has a similar structure to the Skill Pilot project.

config/config/ai_providers.json5 (only need LLM providers, no others like TTS or image)
config/.env saves the Discord bot token
users/{discord_user_id}/
  - user_info.json: username, display name, timezone, next_message_time (for scheduling), etc.
  - system.md: maintained by the system, not by the LLM archive process
  - profile.md: 512 tokens
    - name, timezone, language, role, strong preferences, opt-out status, and major durable facts
    - updated on each archive, kept to about 512 tokens
  - long_term_memory.md: 1k tokens
    - durable interests, repeated objections, recurring goals, repeated product interests, current campaign, recent project, current buying signals, current hesitation, recent life context
    - merged with short_term_memory and summarized to about 1k on each archive
  - short_term_memory.md: 1k tokens
    - open loops, promises, what bot said recently, current emotional tone, next recommended step
    - on archive, summarized and merged into long_term_memory
  - history.jsonl 1k - 3k tokens
    - recent chat history
    - when > 3k, keep the newest 1k, move the portion from 1k to 3k to users/{discord_user_id}/histories/history_chunked_{2026-03-13T1000_1015}.jsonl for later retrieval, and summarize to about 1k tokens and save to short_term_memory.md
  users/{discord_user_id}/archive/
    - archive each file below before updating, with a timestamp, for later audit only — not used by the LLM
    - profile.md,
    - long_term_memory.md,
    - short_term_memory.md

For user files:
1. All files below will serve as LLM input (system message, assistant/user messages)
  - system.md
  - profile.md
  - long_term_memory.md
  - short_term_memory.md
  - history.jsonl

skills/
  - schedule
  - archive

Schedule agent skill: 
  once a message is sent to a user (as the user may not reply), the LLM needs to use the schedule agent skill to figure out when to send the next message if the user does not respond, or if the user indicates they want to stop the conversation or opt out. Then schedule it by invoking a helper python script with discord_user_id to update `user_info.json`.

Archive agent skill:
  Each time before sending a request to the LLM, check the token size in history.jsonl. If archiving is needed, invoke the LLM to use the archive agent skill first, then send the request to the LLM for chat.
  The archive agent skill should use prompt and add help script if need.

When the bot starts its main loop, it also starts the scheduler process. The scheduler checks all user_info.json files by latest updated time. If there is no scheduled time, contact the user immediately; otherwise, contact them at the scheduled time.

If a user initiates a message, auto-create the related files if they do not exist.

The current vibe coding project is located at `workspace/vibe-coding/service-bot`. All code should be created in this folder, do not import from the root project, but you can refer to other code, such as how discord bot immeplemented on the root project.

When needed, give all the information to the LLM and let it decide.

```llm decide
quiet hours by timezone
max messages per week
backoff policy
opt-out 

Good default backoff
If no reply:
1 day
3 days
7 days
14 days
30 days
```

Also, we need configurable rules so the scheduler enforces rules similar to the above in case there is an issue with the LLM's decision, but more loosely, leaving the major decisions to the LLM.
