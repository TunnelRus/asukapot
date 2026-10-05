import os
from typing import cast
import discord
import logging
from config import BACKUP_CHANNEL_ID
from config import DB_PATH

logger = logging.getLogger("Database.CloudSync")

async def restore_database_from_discord(bot: discord.Client) -> None:
    """
    On boot, downloads the most recent .db file from your private Discord
    backup channel so Render's filesystem wipe never loses your settings.
    """
    if not BACKUP_CHANNEL_ID:
        logger.warning("No BACKUP_CHANNEL_ID set. Running with local ephemeral database.")
        return

    try:
        raw_channel = await bot.fetch_channel(BACKUP_CHANNEL_ID)
        # Type guard: Ensure channel supports message history and text uploads
        if not isinstance(raw_channel, discord.TextChannel):
            logger.error(f"Backup channel ID {BACKUP_CHANNEL_ID} is not a valid text channel.")
            return

        channel = cast(discord.TextChannel, raw_channel)

        logger.info("Checking Discord cloud backup channel for database snapshots...")
        async for message in channel.history(limit=10):
            for attachment in message.attachments:
                if attachment.filename.endswith(".db"):
                    data = await attachment.read()
                    with open(DB_PATH, "wb") as f:
                        f.write(data)
                    logger.info(f"Successfully restored database snapshot ({len(data)} bytes) from Discord.")
                    return
        logger.info("No remote database snapshot found in channel. Starting fresh database.")
    except Exception as e:
        logger.error(f"Failed to restore database from Discord backup channel: {e}")

async def backup_database_to_discord(bot: discord.Client) -> None:
    """
    Uploads the current database file to your private Discord backup channel
    and purges older snapshots to keep the channel clean.
    """
    if not BACKUP_CHANNEL_ID or not os.path.exists(DB_PATH):
        return

    try:
        raw_channel = await bot.fetch_channel(BACKUP_CHANNEL_ID)
        if not isinstance(raw_channel, discord.TextChannel):
            return

        channel = cast(discord.TextChannel, raw_channel)

        # Upload the database file as an attachment
        file = discord.File(DB_PATH, filename="honeypot_system.db")
        await channel.send(
            content=f"Database Snapshot • `{discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            file=file
        )
        logger.info("Uploaded fresh database snapshot to Discord backup channel.")

        # Keep only the last 3 snapshots in the channel to prevent clutter
        count = 0
        async for msg in channel.history(limit=10):
            if msg.attachments:
                count += 1
                if count > 3:
                    try:
                        await msg.delete()
                    except discord.DiscordException:
                        pass
    except Exception as e:
        logger.error(f"Failed to upload database snapshot to Discord: {e}")