import datetime
import logging
import discord
from discord.ext import commands

from config import OWNER_IDS
from utils.cache import cache
from utils.helpers import can_punish_member, cleanup_hours_to_ban_days, create_single_use_invite
from utils.ui import create_honeypot_embed, create_softban_dm_embed, HoneypotPersistentView
from repositories.guild_repository import guild_repo
from repositories.reputation_repository import reputation_repo
from services.threat_engine import threat_engine
from services.persona_service import persona_service
from services.incident_service import incident_service

logger = logging.getLogger("Cogs.TrapListener")

class TrapListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Type guard: Ignore DMs, bots, and non-text channels
        if not message.guild or message.author.bot:
            return

        if not isinstance(message.author, discord.Member):
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        author: discord.Member = message.author
        channel: discord.TextChannel = message.channel
        guild: discord.Guild = message.guild

        # 2. Master Owner Permanent Immunity
        if author.id in OWNER_IDS:
            return

        settings = await cache.get(guild.id)
        if not settings or not settings.get("trap_channel_id"):
            return

        if channel.id != settings["trap_channel_id"]:
            return

        # 3. Staff Immunity
        if author.guild_permissions.administrator or author.guild_permissions.manage_guild:
            try:
                await message.delete()
                await channel.send(
                    f"**Notice:** {author.mention}, you have Administrator immunity. Do not test or chat in this channel.",
                    delete_after=4
                )
            except discord.DiscordException:
                pass
            return

        # 4. Whitelist Exemption
        whitelist = await cache.get_whitelist(guild.id)
        if author.id in whitelist or any(role.id in whitelist for role in author.roles):
            try:
                await message.delete()
                await channel.send(
                    f"**Notice:** {author.mention}, you are whitelisted. Avoid typing in the honeypot channel.",
                    delete_after=4
                )
            except discord.DiscordException:
                pass
            return

        # 5. Role Hierarchy Check
        can_punish, reason_hierarchy = can_punish_member(guild, author)
        if not can_punish:
            logger.warning(f"Cannot punish {author} in {guild.name}: {reason_hierarchy}")
            return

        raw_content = message.content or "[Empty / Embed / Attachment]"
        action = (settings.get("action") or "softban").lower()
        cleanup_hours = settings.get("cleanup_hours", 1)
        active_scenario = settings.get("active_scenario", "decoy_operator")

        # 6. Evaluate threat heuristics
        evaluation = threat_engine.evaluate(author, raw_content)

        # 7. Execute persona containment behavior
        await persona_service.execute_scenario(active_scenario, channel, author)

        # 8. Delete intruder message
        try:
            await message.delete()
        except discord.DiscordException:
            pass

        # 9. Progressive reputation update
        reputation = await reputation_repo.record_offense(
            user_id=author.id,
            penalty_points=evaluation.score,
            tag=evaluation.verdict
        )

        if settings.get("auto_escalate", 1) and reputation.current_escalation.value in ("SOFTBAN", "BAN"):
            if reputation.current_escalation.value == "BAN" and action != "ban":
                action = "ban"

        # 10. Generate 1-use invite for recoverable punishments
        invite_url = None
        if action in ("softban", "kick"):
            invite_url = await create_single_use_invite(guild)

        # 11. Send recovery instructions to user
        try:
            dm_embed = create_softban_dm_embed(
                guild_name=guild.name,
                action=action,
                invite_url=invite_url
            )
            await author.send(embed=dm_embed)
        except Exception:
            pass

        # 12. Execute punishment
        audit_reason = f"asukaPot Interception: #{channel.name} | Risk: {evaluation.score}/100"
        ban_days = cleanup_hours_to_ban_days(cleanup_hours)

        try:
            if action == "softban":
                await guild.ban(author, reason=audit_reason, delete_message_days=ban_days)
                await guild.unban(author, reason="asukaPot softban cleanup complete.")
            elif action == "ban":
                await guild.ban(author, reason=audit_reason, delete_message_days=ban_days)
            elif action == "kick":
                await guild.kick(author, reason=audit_reason)
            elif action == "timeout":
                await author.timeout(datetime.timedelta(days=28), reason=audit_reason)
        except discord.Forbidden:
            logger.error(f"Missing permissions to enforce {action} on {author}.")
            return

        # 13. Register formal security incident
        incident = await incident_service.register_incident(
            guild=guild,
            member=author,
            channel=channel,
            evaluation=evaluation,
            raw_content=raw_content,
            action_taken=action
        )

        # 14. Update metrics and notify subsystems
        new_catches = await guild_repo.increment_catches(guild.id)
        cache.invalidate(guild.id)

        self.bot.dispatch("honeypot_trigger", guild, author, action, raw_content, incident)

        # 15. Refresh live honeypot card
        trap_msg_id = settings.get("trap_message_id")
        if trap_msg_id:
            try:
                target_msg = await channel.fetch_message(trap_msg_id)
                new_embed = create_honeypot_embed(action, cleanup_hours, new_catches)
                new_view = HoneypotPersistentView(catches=new_catches)
                await target_msg.edit(embed=new_embed, view=new_view)
            except discord.DiscordException as ex:
                logger.debug(f"Could not refresh trap embed: {ex}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TrapListener(bot))