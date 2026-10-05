import discord
from config import (
    COLOR_AMBER, 
    COLOR_NEUTRAL, 
    COLOR_SUCCESS,
    COLOR_CRIMSON,
    BANNER_IMAGE_URL, 
    PANIC_AVATAR_URL, 
    HUMAN_EXPLANATION_TEXT
)
from utils.formatters import format_action_past
from models.incident import Incident

def create_honeypot_embed(action: str, cleanup_hours: int, catches: int) -> discord.Embed:
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
    embed = discord.Embed(
        title="Honeypot Disarmed",
        description="This channel is no longer active as a security trap. It is now safe to send messages here.",
        color=COLOR_SUCCESS
    )
    embed.set_footer(text="Disarmed by server staff")
    embed.timestamp = discord.utils.utcnow()
    return embed

def create_softban_dm_embed(guild_name: str, action: str, invite_url: str | None = None) -> discord.Embed:
    past_action = format_action_past(action)
    embed = discord.Embed(
        title=f"You were {past_action} in {guild_name}",
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

    # Rejoin link is included for bans, softbans, and kicks
    if invite_url:
        embed.add_field(
            name="Rejoin Link (Valid for 7 Days • 1 Use)",
            value=f"{invite_url}",
            inline=False
        )
    return embed

def create_incident_embed(incident: Incident) -> discord.Embed:
    embed = discord.Embed(
        title="Caught someone in the trap",
        description=f"**{incident.user_name}** triggered the honeypot.",
        color=COLOR_CRIMSON if incident.severity.value in ("CRITICAL", "HIGH") else COLOR_AMBER,
        timestamp=incident.created_at
    )
    embed.add_field(name="Account", value=f"<@{incident.user_id}>\n`{incident.user_name}`", inline=True)
    embed.add_field(name="Action Taken", value=f"**{incident.evidence.get('action_executed', 'softban').upper()}**", inline=True)
    embed.add_field(name="Threat Level", value=f"**{incident.severity.value.capitalize()}**", inline=True)

    flags = incident.evidence.get("flags", [])
    if flags:
        clean_flags = "\n".join([f"• {f}" for f in flags])
        embed.add_field(name="Why it was flagged", value=clean_flags[:1000], inline=False)

    raw_msg = incident.evidence.get("raw_content", "")
    if raw_msg and raw_msg != "[Empty / Embed / Attachment]":
        embed.add_field(name="Intercepted Message", value=f"```{raw_msg[:900]}```", inline=False)

    embed.set_footer(text=f"Incident {incident.incident_id}")
    return embed

class HoneypotPersistentView(discord.ui.View):
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
    embed = discord.Embed(
        title="asukaPot Security Guide",
        description="A complete guide to managing your honeypot traps and investigating threats.",
        color=COLOR_NEUTRAL
    )
    embed.add_field(
        name="Configuration",
        value=(
            "**/honeypot setup [channel]** — Arms a channel and deploys the trap card.\n"
            "**/honeypot disarm** — Safely deactivates honeypot mode.\n"
            "**/honeypot action [action] [cleanup_hours]** — Sets punishment (`Softban`, `Ban`, `Kick`, `Timeout`).\n"
            "**/honeypot scenario [mode]** — Chooses deception persona (`decoy_operator`, `canary_leak`, `silent`).\n"
            "**/honeypot logs [channel]** — Sets your moderation security log channel."
        ),
        inline=False
    )
    embed.add_field(
        name="Investigation & Tools",
        value=(
            "**/honeypot user lookup [user]** — Checks an account's cross-server threat history and previous catches.\n"
            "**/honeypot incident view [id]** — Inspects full evidence for a case file.\n"
            "**/honeypot test rule [text]** — Tests how the threat engine evaluates a sample message.\n"
            "**/honeypot ping** — Quick WebSocket and database latency check.\n"
            "**/honeypot health** — Complete system diagnostics and uptime metrics.\n"
            "**/honeypot upgrade** — Refreshes the pinned trap card to the latest release."
        ),
        inline=False
    )
    embed.add_field(
        name="Whitelist",
        value=(
            "**/honeypot whitelist add [role/user]** — Grants exemption from the trap.\n"
            "**/honeypot whitelist remove [role/user]** — Revokes exemption.\n"
            "**/honeypot status** — Summary of active settings and catch statistics."
        ),
        inline=False
    )
    embed.set_footer(text="asukaPot Security Platform")
    return embed