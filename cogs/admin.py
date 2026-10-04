import discord
from discord import app_commands
from discord.ext import commands
from database import (
    set_honeypot_channel,
    set_log_channel,
    set_punishment_action,
    set_counter_message_id,
    get_guild_settings
)

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    honeypot_group = app_commands.Group(
        name="honeypot",
        description="Configuration suite for the Honeypot security system."
    )

    @honeypot_group.command(name="setup", description="Deploy the trap message into the designated honeypot channel.")
    @app_commands.describe(channel="The channel to act as the honeypot trap.")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        # Set channel in database
        await set_honeypot_channel(interaction.guild_id, channel.id)

        # Ensure correct channel permission warning
        bot_member = interaction.guild.me
        perms = channel.permissions_for(bot_member)
        if not (perms.manage_messages and perms.view_channel):
            await interaction.followup.send(
                f"⚠️ Setup saved, but I need `Manage Messages` and `View Channel` permissions in {channel.mention}!",
                ephemeral=True
            )
            return

        # Construct Honeypot announcement embed matching the requested design
        embed = discord.Embed(
            title="🚫 DO NOT SEND MESSAGES IN THIS CHANNEL",
            description=(
                "**This channel is restricted and used to catch automated spam bots and compromised accounts.**\n\n"
                "Any messages sent here will immediately result in an automated **kick/ban**."
            ),
            color=0xD9381E
        )
        embed.set_thumbnail(url="https://i.imgur.com/KqS7sP7.png") # Visual accent (honey / hazard icon)
        embed.add_field(
            name="📊 Neutralizations",
            value="```fix\nCatches: 0\n```",
            inline=False
        )
        embed.set_footer(text="Automated Defense Array • Evangelion Defense Protocol")

        sent_message = await channel.send(embed=embed)
        await set_counter_message_id(interaction.guild_id, sent_message.id)

        await interaction.followup.send(
            f"✅ Honeypot successfully initialized in {channel.mention}. Trap message pinned and counter tracking active.",
            ephemeral=True
        )

    @honeypot_group.command(name="action", description="Change the punishment applied to caught accounts.")
    @app_commands.describe(mode="The punishment severity to execute.")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Softban (Ban & Unban to delete spam)", value="softban"),
        app_commands.Choice(name="Permanent Ban", value="ban"),
        app_commands.Choice(name="Kick from server", value="kick"),
        app_commands.Choice(name="Timeout for 28 Days", value="timeout")
    ])
    @app_commands.default_permissions(administrator=True)
    async def action(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        await set_punishment_action(interaction.guild_id, mode.value)
        await interaction.response.send_message(
            f"🛡️ Honeypot punishment mode updated to: **{mode.name}**",
            ephemeral=True
        )

    @honeypot_group.command(name="logs", description="Set the moderation log channel for caught triggers.")
    @app_commands.describe(channel="Channel where neutralization logs will be dispatched.")
    @app_commands.default_permissions(administrator=True)
    async def logs(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_log_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            f"📋 Security logs will now be sent to {channel.mention}",
            ephemeral=True
        )

    @honeypot_group.command(name="stats", description="Inspect the active honeypot status and metrics.")
    @app_commands.default_permissions(administrator=True)
    async def stats(self, interaction: discord.Interaction):
        data = await get_guild_settings(interaction.guild_id)
        if not data or not data["channel_id"]:
            await interaction.response.send_message(
                "❌ No Honeypot configured for this server. Use `/honeypot setup` first.",
                ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(data["channel_id"])
        log_channel = interaction.guild.get_channel(data["log_channel_id"]) if data["log_channel_id"] else None

        embed = discord.Embed(
            title="🛡️ Honeypot Status & Defense Metrics",
            color=0x2ECC71
        )
        embed.add_field(name="Trap Channel", value=channel.mention if channel else "None", inline=True)
        embed.add_field(name="Log Channel", value=log_channel.mention if log_channel else "Disabled", inline=True)
        embed.add_field(name="Action Protocol", value=f"`{data['action'].upper()}`", inline=True)
        embed.add_field(name="Total Bots Neutralized", value=f"**{data['trigger_count']}**", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))