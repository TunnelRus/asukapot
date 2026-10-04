import discord
from discord.ext import commands
import time
from collections import defaultdict
import logging
from config import COLOR_CRIMSON

logger = logging.getLogger("Cogs.AntiSpike")

class AntiSpike(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.history = defaultdict(list)
        self.SPIKE_COUNT = 3
        self.SPIKE_WINDOW = 12

    @commands.Cog.listener()
    async def on_honeypot_trigger(self, guild: discord.Guild, member: discord.Member, action: str, content: str):
        now = time.time()
        record = self.history[guild.id]
        
        record = [t for t in record if now - t < self.SPIKE_WINDOW]
        record.append(now)
        self.history[guild.id] = record

        if len(record) >= self.SPIKE_COUNT:
            self.history[guild.id].clear()
            logger.warning(f"Raid spike detected in {guild.name} ({guild.id})")
            await self.trigger_spike_alert(guild)

    async def trigger_spike_alert(self, guild: discord.Guild):
        embed = discord.Embed(
            title="Raid Spike Detected",
            description=(
                f"**{self.SPIKE_COUNT} accounts** triggered the honeypot within **{self.SPIKE_WINDOW} seconds**.\n\n"
                "A mass bot raid or automated token wave is likely hitting the server right now. "
                "Check recent moderation logs and verify your server's safety settings."
            ),
            color=COLOR_CRIMSON
        )
        embed.set_footer(text="Anti-Raid Trigger")
        embed.timestamp = discord.utils.utcnow()

        channel = guild.system_channel
        if channel and channel.permissions_for(guild.me).send_messages:
            try:
                await channel.send(content="@here", embed=embed)
            except discord.DiscordException:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiSpike(bot))