import discord
import logging
from config import DB_PATH
import aiosqlite
from utils.ui import create_honeypot_embed, HoneypotPersistentView
from utils.cache import cache

logger = logging.getLogger("Services.Fleet")

class FleetService:
    """Manages cross-server honeypot health and automated version upgrades."""

    async def auto_upgrade_fleet(self, bot: discord.Client) -> dict:
        """
        Scans all armed honeypots in the database and automatically upgrades
        older embeds and buttons to the latest v2.5.1 design.
        """
        stats = {"scanned": 0, "upgraded": 0, "failed": 0}

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT guild_id, trap_channel_id, trap_message_id, action, cleanup_hours, total_catches FROM guild_settings WHERE trap_channel_id > 0;"
            ) as cursor:
                rows = await cursor.fetchall()

        for row in rows:
            stats["scanned"] += 1
            guild_id = row["guild_id"]
            channel_id = row["trap_channel_id"]
            message_id = row["trap_message_id"]

            guild = bot.get_guild(guild_id)
            if not guild:
                continue

            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                stats["failed"] += 1
                continue

            try:
                msg = await channel.fetch_message(message_id)
                new_embed = create_honeypot_embed(
                    action=row["action"] or "softban",
                    cleanup_hours=row["cleanup_hours"] or 1,
                    catches=row["total_catches"] or 0
                )
                view = HoneypotPersistentView(catches=row["total_catches"] or 0)
                await msg.edit(embed=new_embed, view=view)
                stats["upgraded"] += 1
            except discord.NotFound:
                logger.warning(f"Trap message in guild {guild.name} ({guild_id}) was deleted. Needs redeployment.")
                stats["failed"] += 1
            except Exception as e:
                logger.debug(f"Could not refresh trap in {guild.name}: {e}")
                stats["failed"] += 1

        logger.info(f"Fleet sync complete: {stats['upgraded']} upgraded, {stats['failed']} failed out of {stats['scanned']} armed traps.")
        return stats

fleet_service = FleetService()