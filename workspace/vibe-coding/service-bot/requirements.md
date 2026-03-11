Using git repo git@github.com:Haicam/discord-service-bot.git

Create a discord bot with can talk to discord user by direct private message

Refer to skill pilot project for how to use AI Agent cli as LLM provider
Refer to skill pilot project's discord bot feature for how to save chat history, compress message context, etc to let the AI bot have memory when chat with the user

it have the similar structure as skill pilot project

config/config/ai_providers.json5 (only need llm providers, no others tts, image)
config/.env save discord bot token
users/{discord_user_id}.jsonl 
  - in the beginning, it have the user profile json data, user name, display name, and user profile, next scheduled talking time
  - follow by system message
  - compressed message history(assistant message): if we can have multiple level compressed message rolled by time, so recent message have long content(more details), and older message has short content only important factor (just as real human can forget things after long time)
  - current active message history 
tools/schedule.py: once sent a message to user, LLM need figure out to send another message if user no response, or user indicate to stop the conversation, then schedule it by invoke tools/schedule.py with discord_user_id and the time

When the bot start just in main loop, and then start the scheduler process, the scheduler will check all the files by latest updated time, it no schedule time, contact user immediately, or send as schedule, once success send the message

if user initiate a message, auto create the profile or update it
as any message sent user may not reply, so the llm need to update the user profile file each time for the next schedule time

Do not copy any files from the root project, but you can refer to the code then write from scrach
