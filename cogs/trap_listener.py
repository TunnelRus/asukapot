import discord
from discord.ext import commands
import datetime
import logging
from config import OWNER_IDS, COLOR_CRIMSON
from utils.cache import cache
from utils.helpers import can_punish_member, cleanup_hours_to_ban_days, create_single_use_invite
from utils.ui import create_honeypot_embed, create_softban_dm_embed, HoneypotPersistentView
from database.queries import increment_catches, record_incident_log

logger = logging.getLogger("Cogs.TrapListener")

class TrapListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        # 1. Permanent Bot Owner Immunity
        if message.author.id in OWNER_IDS:
            return

        settings = await cache.get(message.guild.id)
        if not settings or not settings.get("trap_channel_id"):
            return

        # Check if the message is in the configured trap channel
        if message.channel.id != settings["trap_channel_id"]:
            return

        author = message.author
        guild = message.guild

        # 2. Server Administrator Immunity
        if author.guild_permissions.administrator or author.guild_permissions.manage_guild:
            try:
                await message.delete()
                await message.channel.send(
                    f"**Notice:** {author.mention}, you have Administrator immunity. Please do not type in the trap channel.",
                    delete_after=4
                )
            except discord.DiscordException:
                pass
            return

        # 3. Whitelist Check (Immune roles or users)
        whitelist = await cache.get_whitelist(guild.id)
        if author.id in whitelist or any(role.id in whitelist for role in author.roles):
            try:
                await message.delete()
                await message.channel.send(
                    f"**Notice:** {author.mention}, you are whitelisted. Avoid typing in the honeypot channel.",
                    delete_after=4
                )
            except discord.DiscordException:
                pass
            return

        # 4. Role Hierarchy Check
        can_punish, reason_hierarchy = can_punish_member(guild, author)
        if not can_punish:
            logger.warning(f"Cannot punish {author} in {guild.name}: {reason_hierarchy}")
            return

        action = (settings.get("action") or "softban").lower()
        cleanup_hours = settings.get("cleanup_hours", 1)
        raw_content = message.content or "[Empty / Embed / Attachment]"

        # 5. Immediate message deletion
        try:
            await message.delete()
        except discord.DiscordException:
            pass

        # 6. Generate 1-use invite for softbans and kicks
        invite_url = None
        if action in ("softban", "kick"):
            invite_url = await create_single_use_invite(guild)

        # 7. Send recovery DM to user
        try:
            dm_embed = create_softban_dm_embed(
                guild_name=guild.name,
                action=action,
                invite_url=invite_url
            )
            await author.send(embed=dm_embed)
        except Exception:
            pass  # User has DMs closed

        # 8. Execute punishment
        audit_reason = f"Honeypot Trigger: Posted in #{message.channel.name}"
        ban_days = cleanup_hours_to_ban_days(cleanup_hours)

        try:
            if action == "softban":
                await guild.ban(author, reason=audit_reason, delete_message_days=ban_days)
                await guild.unban(author, reason="Honeypot softban wipe completed.")
            elif action == "ban":
                await guild.ban(author, reason=audit_reason, delete_message_days=ban_days)
            elif action == "kick":
                await guild.kick(author, reason=audit_reason)
            elif action == "timeout":
                await author.timeout(datetime.timedelta(days=28), reason=audit_reason)
        except discord.Forbidden:
            logger.error(f"Missing permissions to enforce {action} on {author}.")
            return

        # 9. Record stats and incident report
        new_catches = await increment_catches(guild.id)
        cache.invalidate(guild.id)
        await record_incident_log(guild.id, author.id, str(author), action, raw_content)

        # 10. Dispatch event to mod-log and anti-spike cogs
        self.bot.dispatch("honeypot_trigger", guild, author, action, raw_content)

        # 11. Live update the trap embed counter
        trap_msg_id = settings.get("trap_message_id")
        if trap_msg_id:
            try:
                target_msg = await message.channel.fetch_message(trap_msg_id)
                new_embed = create_honeypot_embed(action, cleanup_hours, new_catches)
                new_view = HoneypotPersistentView(catches=new_catches)
                await target_msg.edit(embed=new_embed, view=new_view)
            except discord.DiscordException as ex:
                logger.debug(f"Could not refresh trap embed: {ex}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TrapListener(bot))