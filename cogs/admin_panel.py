import discord
from discord import app_commands
from discord.ext import commands
from typing import Union
from config import OWNER_IDS
from utils.cache import cache
from utils.helpers import is_admin_or_owner, check_bot_channel_permissions
from utils.ui import (
    create_honeypot_embed, 
    create_disarmed_embed, 
    build_help_embed, 
    HoneypotPersistentView
)
from database.queries import (
    upsert_trap_config, 
    disarm_trap,
    update_punishment, 
    update_log_channel, 
    get_guild_settings,
    get_recent_incidents,
    add_whitelist,
    remove_whitelist,
    get_guild_whitelist
)
from config import COLOR_SUCCESS

class AdminPanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    honeypot_group = app_commands.Group(
        name="honeypot",
        description="Configure and manage the honeypot security system."
    )

    whitelist_subgroup = app_commands.Group(
        name="whitelist",
        description="Manage roles and users that are immune to the honeypot.",
        parent=honeypot_group
    )

    @honeypot_group.command(name="help", description="View the Honeypot manual, setup instructions, and command list.")
    async def help_command(self, interaction: discord.Interaction):
        embed = build_help_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @honeypot_group.command(name="setup", description="Arms a channel and posts the trap message.")
    @app_commands.describe(channel="The channel you want to turn into a trap.")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        valid, msg = check_bot_channel_permissions(channel)
        if not valid:
            await interaction.followup.send(f"**Configuration Error:** {msg}", ephemeral=True)
            return

        settings = await cache.get(interaction.guild_id) or {}
        action = settings.get("action", "softban")
        cleanup_hours = settings.get("cleanup_hours", 1)
        catches = settings.get("total_catches", 0)

        embed = create_honeypot_embed(action, cleanup_hours, catches)
        view = HoneypotPersistentView(catches=catches)
        deployed_msg = await channel.send(embed=embed, view=view)

        await upsert_trap_config(interaction.guild_id, channel.id, deployed_msg.id)
        cache.invalidate(interaction.guild_id)

        await interaction.followup.send(
            f"**Honeypot Active:** Trap successfully deployed in {channel.mention}.",
            ephemeral=True
        )

    @honeypot_group.command(name="disarm", description="Disarms the honeypot and makes the channel safe to type in again.")
    async def disarm(self, interaction: discord.Interaction):
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        old_channel_id, old_message_id = await disarm_trap(interaction.guild_id)
        cache.invalidate(interaction.guild_id)

        if not old_channel_id:
            await interaction.followup.send("There is no active honeypot configured on this server.", ephemeral=True)
            return

        # Clean up or update the old trap embed
        channel = interaction.guild.get_channel(old_channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(old_message_id)
                disarm_embed = create_disarmed_embed()
                await msg.edit(embed=disarm_embed, view=None)
            except discord.DiscordException:
                pass

        await interaction.followup.send(
            f"**Honeypot Disarmed:** The trap in <#{old_channel_id}> has been deactivated. It is now safe to type in that channel.",
            ephemeral=True
        )

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
    async def action(
        self, 
        interaction: discord.Interaction, 
        action: app_commands.Choice[str], 
        cleanup_hours: app_commands.Range[int, 1, 168] = 1
    ):
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await update_punishment(interaction.guild_id, action.value, cleanup_hours)
        cache.invalidate(interaction.guild_id)

        await interaction.response.send_message(
            f"**Updated Settings:** Action set to **{action.name}** with a **{cleanup_hours} hour(s)** message cleanup window.",
            ephemeral=True
        )

    @honeypot_group.command(name="logs", description="Designate a channel for incident reports.")
    @app_commands.describe(channel="Channel where caught accounts are reported.")
    async def logs(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await update_log_channel(interaction.guild_id, channel.id)
        cache.invalidate(interaction.guild_id)

        await interaction.response.send_message(
            f"**Logs Configured:** Incident reports will be sent to {channel.mention}.",
            ephemeral=True
        )

    @honeypot_group.command(name="status", description="Check current honeypot settings and recent incidents.")
    async def status(self, interaction: discord.Interaction):
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)
            return

        settings = await get_guild_settings(interaction.guild_id)
        if not settings or not settings.get("trap_channel_id"):
            await interaction.response.send_message(
                "**Not Configured:** The honeypot is currently not active on this server. Use `/honeypot setup` to arm a channel.",
                ephemeral=True
            )
            return

        trap_channel = interaction.guild.get_channel(settings["trap_channel_id"])
        log_channel = interaction.guild.get_channel(settings["log_channel_id"]) if settings["log_channel_id"] else None
        whitelist_ids = await get_guild_whitelist(interaction.guild_id)

        embed = discord.Embed(title="Honeypot System Status", color=COLOR_SUCCESS)
        embed.add_field(name="Trap Channel", value=trap_channel.mention if trap_channel else "*Missing/Deleted*", inline=True)
        embed.add_field(name="Log Channel", value=log_channel.mention if log_channel else "*Disabled*", inline=True)
        embed.add_field(name="Punishment Mode", value=f"`{settings['action'].upper()}`", inline=True)
        embed.add_field(name="Cleanup Window", value=f"`{settings['cleanup_hours']} hour(s)`", inline=True)
        embed.add_field(name="Total Catches", value=f"**{settings['total_catches']}**", inline=True)
        embed.add_field(name="Whitelisted Roles/Users", value=f"{len(whitelist_ids)}", inline=True)

        recent = await get_recent_incidents(interaction.guild_id, limit=3)
        if recent:
            lines = [f"• `{r['caught_at'][:16]}` | **{r['user_name']}** (`{r['action_taken'].upper()}`)" for r in recent]
            embed.add_field(name="Recent Catches", value="\n".join(lines), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @whitelist_subgroup.command(name="add", description="Add a role or user to the honeypot whitelist.")
    @app_commands.describe(target="The role or user to whitelist.")
    async def whitelist_add(self, interaction: discord.Interaction, target: Union[discord.Role, discord.Member]):
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)
            return

        target_type = "role" if isinstance(target, discord.Role) else "user"
        await add_whitelist(interaction.guild_id, target.id, target_type)
        cache.invalidate(interaction.guild_id)

        await interaction.response.send_message(
            f"**Whitelisted:** {target.mention} will no longer trigger the honeypot.",
            ephemeral=True
        )

    @whitelist_subgroup.command(name="remove", description="Remove a role or user from the whitelist.")
    @app_commands.describe(target="The role or user to remove.")
    async def whitelist_remove(self, interaction: discord.Interaction, target: Union[discord.Role, discord.Member]):
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await remove_whitelist(interaction.guild_id, target.id)
        cache.invalidate(interaction.guild_id)

        await interaction.response.send_message(
            f"**Removed:** {target.mention} is no longer immune to the honeypot.",
            ephemeral=True
        )

    @honeypot_group.command(name="sync", description="Cleans up and re-registers slash commands to fix duplicates.")
    async def sync_commands(self, interaction: discord.Interaction):
        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        synced = await self.bot.tree.sync()

        await interaction.followup.send(
            f"**Commands Refreshed:** Registered {len(synced)} global commands. "
            "If Discord still displays duplicates, press Ctrl + R to refresh your client.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminPanel(bot))