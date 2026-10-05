import time
from collections import defaultdict
import logging
import discord
from discord.ext import commands

from config import COLOR_CRIMSON
from services.alert_manager import alert_manager
from utils.logger import security_logger

logger = logging.getLogger("Cogs.AntiSpike")

class AntiSpike(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.history = defaultdict(list)
        self.SPIKE_COUNT = 3
        self.SPIKE_WINDOW = 12

    @commands.Cog.listener()
    async def on_honeypot_trigger(self, guild: discord.Guild, member: discord.Member, action: str, content: str, incident=None):
        now = time.time()
        record = self.history[guild.id]
        
        record = [t for t in record if now - t < self.SPIKE_WINDOW]
        record.append(now)
        self.history[guild.id] = record

        if len(record) >= self.SPIKE_COUNT:
            self.history[guild.id].clear()
            if alert_manager.should_dispatch(guild.id, "raid_spike"):
                logger.warning(f"Raid spike confirmed in {guild.name} ({guild.id})")
                await self.trigger_spike_alert(guild)

    async def trigger_spike_alert(self, guild: discord.Guild):
        security_logger.log_event(
            event_type="RAID_SPIKE_DETECTED",
            guild_id=guild.id,
            user_id=0,
            correlation_id="SYSTEM-RAID",
            severity="CRITICAL",
            details={"spike_count": self.SPIKE_COUNT, "window": self.SPIKE_WINDOW}
        )

        embed = discord.Embed(
            title="CRITICAL SECURITY ALERT: Coordinated Raid Detected",
            description=(
                f"**{self.SPIKE_COUNT} accounts** triggered the honeypot within **{self.SPIKE_WINDOW} seconds**.\n\n"
                "A mass bot raid or automated token wave is targeting the server. "
                "Staff should verify server permissions, review verification levels, and check moderation logs."
            ),
            color=COLOR_CRIMSON
        )
        embed.set_footer(text="asukaPot Anti-Raid Defense Core")
        embed.timestamp = discord.utils.utcnow()

        channel = guild.system_channel
        if channel and channel.permissions_for(guild.me).send_messages:
            try:
                await channel.send(content="@here", embed=embed)
            except discord.DiscordException:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiSpike(bot))