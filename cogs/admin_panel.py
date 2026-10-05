import time
import re
from typing import Union, Optional
import discord
from discord import app_commands
from discord.ext import commands

from utils.cache import cache
from utils.helpers import is_admin_or_owner, check_bot_channel_permissions
from utils.ui import (
    create_honeypot_embed, 
    create_disarmed_embed, 
    build_help_embed, 
    create_incident_embed,
    HoneypotPersistentView
)
from repositories.guild_repository import guild_repo
from repositories.incident_repository import incident_repo
from repositories.reputation_repository import reputation_repo
from services.threat_engine import threat_engine
from services.fleet_service import fleet_service
from config import COLOR_SUCCESS, COLOR_INFO, COLOR_AMBER, DB_PATH
import aiosqlite

class AdminPanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    honeypot_group = app_commands.Group(
        name="honeypot",
        description="Configure and manage the honeypot security platform."
    )

    whitelist_subgroup = app_commands.Group(
        name="whitelist",
        description="Manage roles and accounts exempted from honeypot containment.",
        parent=honeypot_group
    )

    incident_subgroup = app_commands.Group(
        name="incident",
        description="Investigate and manage security incidents.",
        parent=honeypot_group
    )

    user_subgroup = app_commands.Group(
        name="user",
        description="Inspect reputation and threat history of accounts.",
        parent=honeypot_group
    )

    test_subgroup = app_commands.Group(
        name="test",
        description="Testing and simulation sandbox.",
        parent=honeypot_group
    )

    @honeypot_group.command(name="help", description="View the Honeypot manual, setup instructions, and command list.")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = build_help_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)

    @honeypot_group.command(name="ping", description="Check instant WebSocket and database latency.")
    async def ping_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        start_db = time.perf_counter()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("SELECT 1;")
        db_ms = (time.perf_counter() - start_db) * 1000

        ws_ms = round(self.bot.latency * 1000, 1)

        embed = discord.Embed(
            title="System Latency & Pulse",
            color=COLOR_SUCCESS if ws_ms < 150 else COLOR_AMBER
        )
        embed.add_field(name="Gateway Heartbeat", value=f"`{ws_ms}ms`", inline=True)
        embed.add_field(name="SQLite Read/Write", value=f"`{db_ms:.2f}ms`", inline=True)
        embed.set_footer(text="asukaPot Health Monitor")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @honeypot_group.command(name="health", description="Deep diagnostics, uptime, memory, and fleet status.")
    async def health_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        start = time.perf_counter()
        _ = await guild_repo.get_settings(interaction.guild_id or 0)
        db_latency = (time.perf_counter() - start) * 1000

        uptime_delta = discord.utils.utcnow() - getattr(self.bot, "start_time", discord.utils.utcnow())
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m"

        # Count active traps in DB
        armed_count = 0
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM guild_settings WHERE trap_channel_id > 0;") as cur:
                row = await cur.fetchone()
                armed_count = row[0] if row else 0

        embed = discord.Embed(title="asukaPot Platform Health Matrix", color=COLOR_SUCCESS)
        embed.add_field(name="Gateway Latency", value=f"`{round(self.bot.latency * 1000, 1)}ms`", inline=True)
        embed.add_field(name="Database Speed", value=f"`{db_latency:.2f}ms`", inline=True)
        embed.add_field(name="System Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="Active Guilds", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="Armed Traps", value=f"`{armed_count} channels`", inline=True)
        embed.add_field(name="Memory Cache", value=f"`{len(cache._cache)} guilds cached`", inline=True)
        embed.add_field(name="Status", value="All subsystems nominal • Threat analysis active", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @honeypot_group.command(name="upgrade", description="Self-heals and refreshes the armed honeypot trap to the latest version.")
    async def upgrade_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        settings = await cache.get(interaction.guild_id or 0)
        if not settings or not settings.get("trap_channel_id"):
            await interaction.followup.send("No honeypot is armed on this server. Use `/honeypot setup` first.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(settings["trap_channel_id"]) if interaction.guild else None
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("The armed channel could not be found. Please re-run `/honeypot setup`.", ephemeral=True)
            return

        try:
            msg = await channel.fetch_message(settings["trap_message_id"])
            new_embed = create_honeypot_embed(
                action=settings.get("action", "softban"),
                cleanup_hours=settings.get("cleanup_hours", 1),
                catches=settings.get("total_catches", 0)
            )
            view = HoneypotPersistentView(catches=settings.get("total_catches", 0))
            await msg.edit(embed=new_embed, view=view)
            await interaction.followup.send(f"Successfully refreshed and upgraded the honeypot in {channel.mention} to v2.5.1.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Could not refresh the existing message ({e}). You may re-arm it using `/honeypot setup`.", ephemeral=True)

    @honeypot_group.command(name="setup", description="Arms a channel and deploys the trap message.")
    @app_commands.describe(channel="The channel you want to turn into a trap.")
    async def setup_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild_id: int = interaction.guild_id

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        valid, msg = check_bot_channel_permissions(channel)
        if not valid:
            await interaction.followup.send(f"**Configuration Error:** {msg}", ephemeral=True)
            return

        settings = await cache.get(guild_id) or {}
        action = settings.get("action", "softban")
        cleanup_hours = settings.get("cleanup_hours", 1)
        catches = settings.get("total_catches", 0)

        embed = create_honeypot_embed(action, cleanup_hours, catches)
        view = HoneypotPersistentView(catches=catches)
        deployed_msg = await channel.send(embed=embed, view=view)

        await guild_repo.upsert_trap(guild_id, channel.id, deployed_msg.id)
        cache.invalidate(guild_id)

        await interaction.followup.send(
            f"**Honeypot Active:** Trap successfully deployed in {channel.mention}.",
            ephemeral=True
        )

    @honeypot_group.command(name="disarm", description="Disarms the honeypot and makes the channel safe to type in again.")
    async def disarm_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild: discord.Guild = interaction.guild
        guild_id: int = interaction.guild_id

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        old_channel_id, old_message_id = await guild_repo.disarm(guild_id)
        cache.invalidate(guild_id)

        if not old_channel_id:
            await interaction.followup.send("There is no active honeypot configured on this server.", ephemeral=True)
            return

        channel = guild.get_channel(old_channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                msg = await channel.fetch_message(old_message_id)
                disarm_embed = create_disarmed_embed()
                await msg.edit(embed=disarm_embed, view=None)
            except discord.DiscordException:
                pass

        try:
            await interaction.followup.send(
                f"**Honeypot Disarmed:** The trap in <#{old_channel_id}> has been deactivated.",
                ephemeral=True
            )
        except discord.NotFound:
            pass

    @honeypot_group.command(name="action", description="Change the punishment and message cleanup window.")
    @app_commands.describe(
        action="The punishment applied to caught accounts.",
        cleanup_hours="Hours of message history to purge (1 to 168 hours)."
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Softban (Ban and instant unban to wipe messages)", value="softban"),
        app_commands.Choice(name="Permanent Ban", value="ban"),
        app_commands.Choice(name="Kick from server", value="kick"),
        app_commands.Choice(name="Timeout for 28 Days", value="timeout")
    ])
    async def action_cmd(
        self, 
        interaction: discord.Interaction, 
        action: app_commands.Choice[str], 
        cleanup_hours: app_commands.Range[int, 1, 168] = 1
    ):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild_id: int = interaction.guild_id

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await guild_repo.set_action(guild_id, action.value, cleanup_hours)
        cache.invalidate(guild_id)

        await interaction.followup.send(
            f"**Updated Settings:** Action set to **{action.name}** with a **{cleanup_hours} hour(s)** message cleanup window.",
            ephemeral=True
        )

    @honeypot_group.command(name="scenario", description="Select the active honeypot persona and response profile.")
    @app_commands.describe(mode="Deception scenario mode.")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Decoy Operator (Natural typing jitter)", value="decoy_operator"),
        app_commands.Choice(name="Canary Leak (Simulates verification challenge)", value="canary_leak"),
        app_commands.Choice(name="Silent (Immediate silent purge)", value="silent")
    ])
    async def scenario_cmd(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild_id: int = interaction.guild_id

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await guild_repo.set_scenario(guild_id, mode.value)
        cache.invalidate(guild_id)

        await interaction.followup.send(
            f"**Scenario Updated:** Honeypot deception profile set to **{mode.name}**.",
            ephemeral=True
        )

    @honeypot_group.command(name="logs", description="Designate a channel for incident reports.")
    @app_commands.describe(channel="Channel where caught accounts are reported.")
    async def logs_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild_id: int = interaction.guild_id

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await guild_repo.set_logs(guild_id, channel.id)
        cache.invalidate(guild_id)

        await interaction.followup.send(
            f"**Logs Configured:** Incident reports will be sent to {channel.mention}.",
            ephemeral=True
        )

    @honeypot_group.command(name="status", description="Check current honeypot settings and recent incidents.")
    async def status_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild or not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild: discord.Guild = interaction.guild
        guild_id: int = interaction.guild_id

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        settings = await guild_repo.get_settings(guild_id)
        if not settings or not settings.get("trap_channel_id"):
            await interaction.followup.send(
                "**Not Configured:** The honeypot is currently not active on this server. Use `/honeypot setup` to arm a channel.",
                ephemeral=True
            )
            return

        trap_channel = guild.get_channel(settings["trap_channel_id"])
        log_channel = guild.get_channel(settings["log_channel_id"]) if settings["log_channel_id"] else None
        whitelist_ids = await guild_repo.get_whitelist(guild_id)

        embed = discord.Embed(title="Honeypot System Status", color=COLOR_SUCCESS)
        embed.add_field(name="Trap Channel", value=trap_channel.mention if trap_channel else "*Missing/Deleted*", inline=True)
        embed.add_field(name="Log Channel", value=log_channel.mention if log_channel else "*Disabled*", inline=True)
        embed.add_field(name="Punishment Mode", value=f"`{settings['action'].upper()}`", inline=True)
        embed.add_field(name="Deception Scenario", value=f"`{settings.get('active_scenario', 'decoy_operator')}`", inline=True)
        embed.add_field(name="Cleanup Window", value=f"`{settings['cleanup_hours']} hour(s)`", inline=True)
        embed.add_field(name="Total Catches", value=f"**{settings['total_catches']}**", inline=True)
        embed.add_field(name="Whitelisted Entities", value=f"{len(whitelist_ids)}", inline=True)

        recent = await incident_repo.get_guild_incidents(guild_id, limit=3)
        if recent:
            lines = [f"• `{r.created_at.strftime('%Y-%m-%d %H:%M')}` | **{r.user_name}** (`{r.severity.value}`)" for r in recent]
            embed.add_field(name="Recent Incidents", value="\n".join(lines), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @incident_subgroup.command(name="view", description="Inspect an incident case file by ID.")
    @app_commands.describe(incident_id="The incident ID (e.g. INC-20261005-XXXXXX)")
    async def incident_view(self, interaction: discord.Interaction, incident_id: str):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions.", ephemeral=True)
            return

        incident = await incident_repo.get_incident(incident_id.strip().upper())
        if not incident or incident.guild_id != interaction.guild_id:
            await interaction.followup.send(f"Incident `{incident_id}` not found for this server.", ephemeral=True)
            return

        embed = create_incident_embed(incident)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @incident_subgroup.command(name="resolve", description="Close an incident case with an audit note.")
    @app_commands.describe(incident_id="The incident ID to resolve", note="Resolution rationale")
    async def incident_resolve(self, interaction: discord.Interaction, incident_id: str, note: str):
        await interaction.response.defer(ephemeral=True)

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions.", ephemeral=True)
            return

        success = await incident_repo.resolve_incident(incident_id.strip().upper(), f"{interaction.user.name}: {note}")
        if success:
            await interaction.followup.send(f"Case `{incident_id}` successfully resolved.", ephemeral=True)
        else:
            await interaction.followup.send(f"Could not resolve `{incident_id}`: Case not found.", ephemeral=True)

    # SMART UNIVERSAL LOOKUP COMMAND
    @user_subgroup.command(name="lookup", description="Search threat reputation by mention, User ID, or raw username.")
    @app_commands.describe(user="The username, User ID, or @mention of the account")
    async def user_lookup(self, interaction: discord.Interaction, user: str):
        """
        Accepts any input (mention, ID, or raw username) and searches
        both Discord and the incident database.
        """
        await interaction.response.defer(ephemeral=True)

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions to use this command.", ephemeral=True)
            return

        target_id: Optional[int] = None
        target_name: Optional[str] = None
        user_obj: Optional[Union[discord.User, discord.Member]] = None

        # 1. Check if user input contains digits (Snowflake ID or Mention)
        cleaned_id = re.sub(r'\D', '', user)
        if len(cleaned_id) >= 17:
            target_id = int(cleaned_id)
            try:
                user_obj = await self.bot.fetch_user(target_id)
                target_name = str(user_obj)
            except discord.NotFound:
                target_name = f"Unknown User (`{target_id}`)"
            except Exception:
                target_name = f"User (`{target_id}`)"

        # 2. If not an ID, search database by username
        if not target_id:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT user_id, user_name FROM incidents WHERE user_name LIKE ? ORDER BY created_at DESC LIMIT 1;",
                    (f"%{user}%",)
                ) as cur:
                    row = await cur.fetchone()
                    if row:
                        target_id = row["user_id"]
                        target_name = row["user_name"]

        # 3. If still not found, search current server members by username
        if not target_id and interaction.guild:
            for member in interaction.guild.members:
                if member.name.lower() == user.lower() or (member.global_name and member.global_name.lower() == user.lower()):
                    target_id = member.id
                    target_name = str(member)
                    user_obj = member
                    break

        # 4. If completely unknown
        if not target_id:
            await interaction.followup.send(
                f"No account or past incidents found matching `{user}`.\n"
                "If the account was already banned and left no prior records, please look them up using their 18-digit Discord User ID.",
                ephemeral=True
            )
            return

        rep = await reputation_repo.get_or_create(target_id)

        embed = discord.Embed(
            title=f"Actor Profile: {target_name or target_id}",
            description=f"Cross-server behavioral threat reputation: `{rep.reputation_score}/100`",
            color=COLOR_INFO
        )
        if user_obj:
            embed.set_thumbnail(url=user_obj.display_avatar.url)

        embed.add_field(name="Account ID", value=f"`{target_id}`", inline=True)
        embed.add_field(name="Offenses Logged", value=str(rep.offense_count), inline=True)
        embed.add_field(name="Current Escalation", value=f"`{rep.current_escalation.value}`", inline=True)
        embed.add_field(name="First Seen", value=discord.utils.format_dt(rep.first_seen, style="R"), inline=True)
        embed.add_field(name="Tags", value=", ".join(rep.tags) if rep.tags else "None", inline=False)

        # Pull recent incidents for this user
        recent_cases = []
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT incident_id, severity, created_at FROM incidents WHERE user_id = ? ORDER BY created_at DESC LIMIT 3;",
                (target_id,)
            ) as cur:
                rows = await cur.fetchall()
                recent_cases = [f"• `{r['incident_id']}` ({r['severity']}) on `{r['created_at'][:10]}`" for r in rows]

        if recent_cases:
            embed.add_field(name="Recent Incident Cases", value="\n".join(recent_cases), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @test_subgroup.command(name="rule", description="Sandbox evaluation of message text against the ThreatEngine.")
    @app_commands.describe(text="The sample message payload to evaluate")
    async def test_rule(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer(ephemeral=True)

        if not isinstance(interaction.user, discord.Member):
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        member: discord.Member = interaction.user

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions.", ephemeral=True)
            return

        eval_res = threat_engine.evaluate(member, text)

        embed = discord.Embed(title="ThreatEngine Sandbox Evaluation", color=COLOR_INFO)
        embed.add_field(name="Risk Score", value=eval_res.risk_bar, inline=True)
        embed.add_field(name="Verdict", value=f"`{eval_res.verdict}`", inline=True)
        embed.add_field(name="Entropy", value=str(eval_res.entropy), inline=True)
        embed.add_field(name="Flags Triggered", value="\n".join([f"• {f}" for f in eval_res.flags]), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @whitelist_subgroup.command(name="add", description="Add a role or user to the honeypot whitelist.")
    @app_commands.describe(target="The role or user to whitelist.")
    async def whitelist_add(self, interaction: discord.Interaction, target: Union[discord.Role, discord.Member]):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild_id: int = interaction.guild_id

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions.", ephemeral=True)
            return

        target_type = "role" if isinstance(target, discord.Role) else "user"
        await guild_repo.add_whitelist(guild_id, target.id, target_type)
        cache.invalidate(guild_id)

        await interaction.followup.send(f"**Whitelisted:** {target.mention} will no longer trigger the honeypot.", ephemeral=True)

    @whitelist_subgroup.command(name="remove", description="Remove a role or user from the whitelist.")
    @app_commands.describe(target="The role or user to remove.")
    async def whitelist_remove(self, interaction: discord.Interaction, target: Union[discord.Role, discord.Member]):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild_id:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild_id: int = interaction.guild_id

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions.", ephemeral=True)
            return

        await guild_repo.remove_whitelist(guild_id, target.id)
        cache.invalidate(guild_id)

        await interaction.followup.send(f"**Removed:** {target.mention} is no longer exempt.", ephemeral=True)

    @honeypot_group.command(name="sync", description="Cleans up and re-registers slash commands to fix duplicates.")
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("This command must be run inside a server.", ephemeral=True)
            return

        guild: discord.Guild = interaction.guild

        if not is_admin_or_owner(interaction):
            await interaction.followup.send("You need Administrator permissions.", ephemeral=True)
            return

        self.bot.tree.clear_commands(guild=guild)
        await self.bot.tree.sync(guild=guild)
        synced = await self.bot.tree.sync()

        await interaction.followup.send(
            f"**Commands Refreshed:** Registered {len(synced)} global commands. (Press Ctrl + R to refresh Discord cache).",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminPanel(bot))