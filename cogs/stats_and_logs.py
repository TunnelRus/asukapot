import discord
from discord.ext import commands
from utils.cache import cache
from utils.ui import create_incident_embed
from models.incident import Incident

class StatsAndLogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_honeypot_trigger(self, guild: discord.Guild, member: discord.Member, action: str, content: str, incident: Incident | None = None):
        settings = await cache.get(guild.id)
        if not settings or not settings.get("log_channel_id"):
            return

        log_channel = guild.get_channel(settings["log_channel_id"])
        # Type narrowing: ensure channel has .send()
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            return

        if incident:
            embed = create_incident_embed(incident)
            try:
                await log_channel.send(embed=embed)
            except discord.DiscordException:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsAndLogs(bot))