import discord
from discord.ext import commands
from utils.cache import cache
from utils.formatters import format_action_past
from utils.intelligence import analyze_intruder_risk
from config import COLOR_CRIMSON, LOG_MESSAGE_CONTENT

class StatsAndLogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_honeypot_trigger(self, guild: discord.Guild, member: discord.Member, action: str, content: str):
        settings = await cache.get(guild.id)
        if not settings or not settings.get("log_channel_id"):
            return

        log_channel = guild.get_channel(settings["log_channel_id"])
        if not log_channel:
            return

        past_action = format_action_past(action)
        risk_note = analyze_intruder_risk(member, content)

        # Natural, humanized staff log card
        embed = discord.Embed(
            title="Caught someone in the trap",
            color=COLOR_CRIMSON,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Account", value=f"{member.mention}\n`{member.name}`", inline=True)
        embed.add_field(name="Action Taken", value=f"**{past_action.upper()}**", inline=True)
        embed.add_field(name="Account Age", value=discord.utils.format_dt(member.created_at, style="R"), inline=True)
        embed.add_field(name="Joined Server", value=discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Triggered In", value=f"<#{settings['trap_channel_id']}>", inline=True)
        embed.add_field(name="Total Catches", value=str(settings.get("total_catches", 0) + 1), inline=True)
        embed.add_field(name="Risk Assessment", value=f"*{risk_note}*", inline=False)
        
        if LOG_MESSAGE_CONTENT:
            cleaned = discord.utils.escape_markdown(content[:900])
            embed.add_field(name="Intercepted Message", value=f"```{cleaned}```", inline=False)
        else:
            embed.add_field(name="Intercepted Message", value="*[Message content logging is disabled]*", inline=False)

        embed.set_footer(text="Honeypot Audit Logging")

        try:
            await log_channel.send(embed=embed)
        except discord.DiscordException:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsAndLogs(bot))