import discord
from discord.ext import commands
import datetime
import logging
from database import get_guild_settings, increment_catches

logger = logging.getLogger("HoneypotCog")

class Honeypot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore DMs and bot messages (avoid loop triggers)
        if not message.guild or message.author.bot:
            return

        settings = await get_guild_settings(message.guild.id)
        if not settings or not settings["channel_id"]:
            return

        # Check if message is in the configured honeypot channel
        if message.channel.id != settings["channel_id"]:
            return

        member = message.author
        guild = message.guild

        # Immunity check for administrators to avoid locking out server staff
        if member.guild_permissions.administrator:
            try:
                await message.delete()
                warn = await message.channel.send(
                    f"⚠️ {member.mention}, you have Administrator immunity, but please do not type in the trap channel.",
                    delete_after=4
                )
            except Exception:
                pass
            return

        # Check role hierarchy to ensure the bot has permission to punish
        if guild.me.top_role <= member.top_role:
            logger.warning(f"Failed to punish {member} in {guild.name}: Member has a higher or equal role.")
            return

        action = (settings["action"] or "softban").lower()
        trigger_count = await increment_catches(guild.id)

        # Cache content before deleting
        raw_content = message.content or "[Empty / Attachment / Embed]"
        
        # 1. Immediately delete the intruder message
        try:
            await message.delete()
        except discord.DiscordException:
            pass

        # 2. Inform the member via DM prior to punishment
        try:
            dm_embed = discord.Embed(
                title="🛡️ Honeypot Defense Triggered",
                description=(
                    f"You posted in a flagged trap channel inside **{guild.name}**.\n"
                    "This channel is strictly used to isolate compromised accounts and malicious raid bots."
                ),
                color=0xE74C3C,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            dm_embed.add_field(name="Action Taken", value=action.upper(), inline=True)
            dm_embed.add_field(name="Account Compromised?", value="If you did not do this manually, change your Discord password immediately and enable 2FA.", inline=False)
            await member.send(embed=dm_embed)
        except Exception:
            # DMs might be disabled; ignore failure and proceed
            pass

        # 3. Execute Punishment
        reason = f"Security: Honeypot trap triggered in #{message.channel.name}"
        try:
            if action == "softban":
                await guild.ban(member, reason=reason, delete_message_days=1)
                await guild.unban(member, reason="Softban cycle complete: Intruder message purged.")
            elif action == "ban":
                await guild.ban(member, reason=reason, delete_message_days=1)
            elif action == "kick":
                await guild.kick(member, reason=reason)
            elif action == "timeout":
                await member.timeout(datetime.timedelta(days=28), reason=reason)
        except discord.Forbidden:
            logger.error(f"Missing permissions to enforce '{action}' on {member} in {guild.name}.")
            return

        # 4. Dispatch Audit/Mod Log
        if settings["log_channel_id"]:
            log_chan = guild.get_channel(settings["log_channel_id"])
            if log_chan:
                log_embed = discord.Embed(
                    title="🚨 Intruder Neutralized",
                    color=0xCC0000,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                log_embed.set_thumbnail(url=member.display_avatar.url)
                log_embed.add_field(name="Account", value=f"{member.mention} (`{member.id}`)", inline=True)
                log_embed.add_field(name="Action Taken", value=action.upper(), inline=True)
                log_embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, style="R"), inline=True)
                log_embed.add_field(name="Interception Channel", value=message.channel.mention, inline=True)
                log_embed.add_field(name="Total Counter", value=str(trigger_count), inline=True)
                log_embed.add_field(name="Trigger Content", value=f"```{raw_content[:900]}```", inline=False)
                await log_chan.send(embed=log_embed)

        # 5. Live update the Honeypot embed counter in the trap channel
        if settings["counter_message_id"]:
            try:
                trap_msg = await message.channel.fetch_message(settings["counter_message_id"])
                if trap_msg and trap_msg.embeds:
                    updated_embed = trap_msg.embeds[0]
                    # Update the button-like display or field
                    updated_embed.set_field_at(
                        0,
                        name="📊 Neutralizations",
                        value=f"```fix\nCatches: {trigger_count}\n```",
                        inline=False
                    )
                    await trap_msg.edit(embed=updated_embed)
            except discord.NotFound:
                pass
            except Exception as e:
                logger.warning(f"Failed updating counter message: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Honeypot(bot))