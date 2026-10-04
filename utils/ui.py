import discord
from config import (
    COLOR_AMBER, 
    COLOR_NEUTRAL, 
    COLOR_SUCCESS,
    BANNER_IMAGE_URL, 
    PANIC_AVATAR_URL, 
    HUMAN_EXPLANATION_TEXT
)
from utils.formatters import format_action_past

def create_honeypot_embed(action: str, cleanup_hours: int, catches: int) -> discord.Embed:
    """Builds the main trap embed."""
    action_clean = action.lower()
    embed = discord.Embed(
        title="🍯 HONEYPOT • DO NOT TYPE HERE",
        description=(
            "This channel is a **trap** for spam bots and hijacked accounts.\n"
            "Real members never need to post here, so if you do you will receive "
            f"a **{action_clean}** (kicked out and messages wiped) **instantly**.\n\n"
            "> Don't say hi. Don't test it. Don't post an emoji.\n"
            "> Just scroll past."
        ),
        color=COLOR_AMBER
    )

    cleanup_text = f"{cleanup_hours} hour{'s' if cleanup_hours > 1 else ''} of messages"
    embed.add_field(name="📦 Punishment", value=action.capitalize(), inline=True)
    embed.add_field(name="🧹 Cleanup", value=cleanup_text, inline=True)
    embed.add_field(name="🕸️ Caught so far", value=str(catches), inline=True)

    embed.set_image(url=BANNER_IMAGE_URL)
    embed.set_footer(text="Honeypot Active")
    embed.timestamp = discord.utils.utcnow()
    return embed

def create_disarmed_embed() -> discord.Embed:
    """Builds the embed shown when a trap channel is disarmed."""
    embed = discord.Embed(
        title="Honeypot Disarmed",
        description=(
            "This channel is no longer active as a security trap. "
            "It is now safe to send messages here."
        ),
        color=COLOR_SUCCESS
    )
    embed.set_footer(text="Disarmed by server staff")
    embed.timestamp = discord.utils.utcnow()
    return embed

def create_softban_dm_embed(guild_name: str, action: str, invite_url: str | None = None) -> discord.Embed:
    """Builds the DM notice sent to users when they trigger the trap."""
    past_tense_action = format_action_past(action)

    embed = discord.Embed(
        title=f"You were {past_tense_action} in {guild_name}",
        description=(
            "You sent a message in a honeypot security trap channel.\n\n"
            "**If your account was compromised, complete these steps immediately:**\n"
            "1. Change your Discord password\n"
            "2. Enable Two-Factor Authentication (2FA)\n"
            "3. Revoke unknown sessions in *Settings → Authorized Apps*\n"
            "4. Terminate active sessions on external devices"
        ),
        color=COLOR_AMBER
    )
    embed.set_thumbnail(url=PANIC_AVATAR_URL)

    if invite_url:
        embed.add_field(
            name="Rejoin Link (Valid for 7 Days • 1 Use)",
            value=f"{invite_url}",
            inline=False
        )

    return embed

class HoneypotPersistentView(discord.ui.View):
    """Persistent button row beneath the trap embed."""
    def __init__(self, catches: int = 0):
        super().__init__(timeout=None)
        
        self.counter_btn = discord.ui.Button(
            label=f"Kicks: {catches}",
            style=discord.ButtonStyle.secondary,
            emoji="🍯",
            disabled=True,
            custom_id="honeypot_persistent_counter"
        )
        self.add_item(self.counter_btn)

    @discord.ui.button(
        label="What is this?",
        style=discord.ButtonStyle.secondary,
        emoji="❓",
        custom_id="honeypot_persistent_info"
    )
    async def explain_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Channel Security Overview",
            description=HUMAN_EXPLANATION_TEXT,
            color=COLOR_AMBER
        )
        embed.set_footer(text="Read channel names carefully to avoid automated penalties.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

def build_help_embed() -> discord.Embed:
    """Builds the clear, humanized staff guide."""
    embed = discord.Embed(
        title="Honeypot Security Guide",
        description=(
            "This bot catches self-bots and hijacked user accounts before they can post spam "
            "across the rest of your server.\n\n"
            "**How It Works:**\n"
            "• Create a channel (like `#do-not-type`) and arm it with `/honeypot setup`.\n"
            "• Normal members read channel names and ignore it.\n"
            "• Bots and token scrapers post into every channel blindly and trigger the trap.\n"
            "• The bot wipes their message instantly, kicks or softbans them, and sends them a DM with a 1-use rejoin link in case their account was hijacked."
        ),
        color=COLOR_NEUTRAL
    )

    embed.add_field(
        name="Available Commands",
        value=(
            "**/honeypot setup [channel]**\n"
            "Arms the chosen channel and posts the trap message.\n\n"
            "**/honeypot disarm**\n"
            "Completely turns off the trap and makes the channel safe to type in again.\n\n"
            "**/honeypot action [action] [cleanup_hours]**\n"
            "Choose between Softban, Ban, Kick, or Timeout, and how many hours of messages to delete.\n\n"
            "**/honeypot logs [channel]**\n"
            "Sets the channel where incident reports and account risk ratings are sent.\n\n"
            "**/honeypot whitelist add [role or user]**\n"
            "Gives a specific role or user immunity so they never trigger the trap.\n\n"
            "**/honeypot whitelist remove [role or user]**\n"
            "Removes someone from the whitelist.\n\n"
            "**/honeypot status**\n"
            "Shows your current settings, total catches, and recent logs.\n\n"
            "**/honeypot sync**\n"
            "Cleans up and fixes duplicate commands in your slash command list."
        ),
        inline=False
    )

    embed.add_field(
        name="Important Tips",
        value=(
            "• **Role Hierarchy:** The bot's role must be higher than regular member roles in *Server Settings → Roles*.\n"
            "• **Server Admins:** Server administrators and bot owners are automatically immune to the trap."
        ),
        inline=False
    )

    embed.set_footer(text="Honeypot Bot • Simple and reliable protection")
    return embed