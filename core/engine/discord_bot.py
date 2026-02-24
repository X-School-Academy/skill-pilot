import asyncio
from typing import List

import discord
from discord.ext import commands

from discord_session import SessionManager
from llm_service import llm_get_text
from settings import get_discord_bot_token, logger

DISCORD_MSG_LIMIT = 2000
SYSTEM_PROMPT = "You are an AI personal assistant to help user to do any work on behalf of the user."

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

session_manager = SessionManager()


def _split_message(text: str, limit: int = DISCORD_MSG_LIMIT) -> List[str]:
    if len(text) <= limit:
        return [text]
    chunks: List[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


def _get_llm_response(messages: list) -> str:
    system_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    return llm_get_text(system_messages + messages)


@bot.event
async def on_ready() -> None:
    logger.info("Discord bot %s is ready, in %d guild(s)", bot.user, len(bot.guilds))
    session_manager.load_all()


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    channel_id = str(message.channel.id)
    session = session_manager.get_or_create(channel_id)

    # Keep the display name fresh. For DMs the author's display name is the
    # human's name; for guild channels use the channel name.
    is_dm = isinstance(message.channel, discord.DMChannel)
    display_name = (
        message.author.display_name if is_dm
        else getattr(message.channel, "name", channel_id)
    )
    if not session.channel_name:
        session.set_channel_info(display_name, is_dm)

    # Per-channel lock prevents concurrent mutations to the same session
    # (interleaved buffer writes, out-of-order context, inconsistent cache).
    async with session._lock:
        session.add_message("user", message.content)

        llm_messages = session.get_llm_messages()

        async with message.channel.typing():
            try:
                reply_text = await asyncio.to_thread(_get_llm_response, llm_messages)
            except Exception as exc:
                logger.error("Discord LLM error channel=%s: %s", channel_id, exc)
                reply_text = "Sorry, I encountered an error processing your message."

        session.add_message("assistant", reply_text)

        if session.needs_summarisation():
            try:
                await asyncio.to_thread(session.summarise, lambda msgs: llm_get_text(msgs))
            except Exception as exc:
                logger.warning("Discord session summarisation failed channel=%s: %s", channel_id, exc)

    for chunk in _split_message(reply_text):
        await message.channel.send(chunk)


async def send_dm_to_all(text: str) -> int:
    sent = 0
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            try:
                dm_channel = await member.create_dm()
                for chunk in _split_message(text):
                    await dm_channel.send(chunk)
                sent += 1
            except discord.Forbidden:
                logger.warning("Cannot DM member %s (DMs disabled)", member)
            except Exception as exc:
                logger.warning("Failed to DM member %s: %s", member, exc)
    return sent


async def start_bot(token: str | None = None) -> None:
    bot_token = (token or get_discord_bot_token()).strip()
    if not bot_token:
        logger.warning("DISCORD_BOT_TOKEN not set, Discord bot will not start")
        return
    await bot.start(bot_token)
