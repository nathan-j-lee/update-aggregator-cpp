import os

import discord
from dotenv import load_dotenv

load_dotenv()

def parse_id_list(variable_name: str) -> set[int]:
    """Convert a comma-separated environment variable into Discord IDs."""
    raw_value = os.getenv(variable_name, "")
    
    return {
        int(value.strip())
        for value in raw_value.split(",")
        if value.strip()
    }

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TRIGGER_EMOJI = os.getenv("DISCORD_TRIGGER_EMOJI", "📌")

coordinator_id = os.getenv("DISCORD_COORDINATOR_USER_ID")
COORDINATOR_USER_ID = int(coordinator_id) if coordinator_id else None

ALLOWED_GUILD_IDS = parse_id_list("DISCORD_ALLOWED_GUILD_IDS")
ALLOWED_CHANNEL_IDS = parse_id_list("DISCORD_ALLOWED_CHANNEL_IDS")

if not BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is missing from .env")

if COORDINATOR_USER_ID is None:
    raise RuntimeError("DISCORD_COORDINATOR_USER_ID is missing from .env")

if not ALLOWED_GUILD_IDS:
    raise RuntimeError("DISCORD_ALLOWED_GUILD_IDS is missing from .env")

if not ALLOWED_CHANNEL_IDS:
    raise RuntimeError("DISCORD_ALLOWED_CHANNEL_IDS is missing from .env")

intents = discord.Intents.default()
intents.guilds = True
intents.reactions = True
intents.message_content = True

bot = discord.Client(intents=intents)

# Temporary duplicate protection for this test.
# This will eventually be replaced with persistent storage.
processed_message_ids: set[int] = set()

@bot.event
async def on_ready() -> None:
    print(f"Connected as {bot.user}")
    print(f"Monitoring {len(ALLOWED_GUILD_IDS)} server(s)")
    print(f"Monitoring {len(ALLOWED_CHANNEL_IDS)} channel(s)")
    print(f"Trigger emoji: {TRIGGER_EMOJI}")
    
@bot.event
async def on_raw_reaction_add(
    payload: discord.RawReactionActionEvent,
) -> None:
    # Ignore direct messages.
    if payload.guild_id is None:
        return

    # Only accept reactions made by the coordinator.
    if payload.user_id != COORDINATOR_USER_ID:
        return

    # Only accept the configured emoji.
    if str(payload.emoji) != TRIGGER_EMOJI:
        return

    # Only accept approved servers and channels.
    if payload.guild_id not in ALLOWED_GUILD_IDS:
        return

    if payload.channel_id not in ALLOWED_CHANNEL_IDS:
        return

    # Avoid processing the same message more than once during this run.
    if payload.message_id in processed_message_ids:
        return
    
    try:
        channel = bot.get_channel(payload.channel_id)

        if channel is None:
            channel = await bot.fetch_channel(payload.channel_id)

        message = await channel.fetch_message(payload.message_id)

        # Do not process messages written by bots.
        if message.author.bot:
            return

        processed_message_ids.add(payload.message_id)

        print("\n--- Captured project update ---")
        print(f"Server: {message.guild.name}")
        print(f"Channel: {message.channel}")
        print(f"Author: {message.author}")
        print(f"Timestamp: {message.created_at}")
        print(f"Message ID: {message.id}")
        print(f"Message URL: {message.jump_url}")
        print(f"Content: {message.content}")

        if message.attachments:
            print("Attachments:")

            for attachment in message.attachments:
                print(f"- {attachment.url}")

        print("--------------------------------\n")

        # Confirm that the bot captured the message.
        await message.add_reaction("✅")

    except discord.Forbidden:
        print(
            "The bot does not have permission to read or react "
            f"in channel {payload.channel_id}."
        )
    except discord.NotFound:
        print("The selected message or channel no longer exists.")
    except discord.HTTPException as error:
        print(f"Discord API error: {error}")


bot.run(BOT_TOKEN)