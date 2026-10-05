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

    if invite_url:
        embed.add_field(
            name="Rejoin Link (Valid for 7 Days • 1 Use)",
            value=f"{invite_url}",
            inline=False
        )
    return embed

def create_incident_embed(incident: Incident) -> discord.Embed:
    embed = discord.Embed(
        title=f"Incident File: {incident.incident_id}",
        description=f"**{incident.title}**\n{incident.summary}",
        color=COLOR_CRIMSON if incident.severity.value in ("CRITICAL", "HIGH") else COLOR_AMBER,
        timestamp=incident.created_at
    )
    embed.add_field(name="Severity", value=f"`{incident.severity.value}`", inline=True)
    embed.add_field(name="Status", value=f"`{incident.status.value}`", inline=True)
    embed.add_field(name="Risk Score", value=f"`{incident.risk_score}/100`", inline=True)
    embed.add_field(name="Correlation ID", value=f"`{incident.correlation_id}`", inline=True)

    evidence = incident.evidence
    embed.add_field(name="Join Delta", value=evidence.get("join_delta", "N/A"), inline=True)
    embed.add_field(name="Entropy", value=str(evidence.get("entropy", "N/A")), inline=True)

    flags = evidence.get("flags", [])
    if flags:
        embed.add_field(name="Flags", value="\n".join([f"• {f}" for f in flags])[:1000], inline=False)

    if incident.notes:
        embed.add_field(name="Case Notes", value="\n".join(incident.notes)[-1000:], inline=False)

    embed.set_footer(text="asukaPot Incident Management Subsystem")
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
        title="asukaPot Security Suite • Command Manual",
        description="Autonomous defense, incident investigation, and honeypot persona management.",
        color=COLOR_NEUTRAL
    )
    embed.add_field(
        name="Configuration",
        value=(
            "**/honeypot setup [channel]** — Arms channel and deploys the trap card.\n"
            "**/honeypot disarm** — Safely deactivates honeypot mode.\n"
            "**/honeypot action [action] [cleanup_hours]** — Sets containment action and message purge window.\n"
            "**/honeypot logs [channel]** — Designates moderation security log stream.\n"
            "**/honeypot scenario [name]** — Sets deception mode (`decoy_operator`, `canary_leak`, `silent`)."
        ),
        inline=False
    )
    embed.add_field(
        name="Forensics & Investigation",
        value=(
            "**/honeypot incident view [id]** — Inspects full evidence card and correlation logs.\n"
            "**/honeypot incident resolve [id] [note]** — Resolves an open case with staff audit notes.\n"
            "**/honeypot user lookup [user]** — Checks cross-server reputation, penalties, and tenure.\n"
            "**/honeypot test rule [text]** — Evaluates payload against threat heuristics.\n"
            "**/honeypot health** — Displays diagnostics, database status, and cache integrity."
        ),
        inline=False
    )
    embed.add_field(
        name="Access Control",
        value=(
            "**/honeypot whitelist add [target]** — Grants exemption to a role or user.\n"
            "**/honeypot whitelist remove [target]** — Revokes honeypot exemption.\n"
            "**/honeypot status** — Summary of active settings and catch statistics.\n"
            "**/honeypot sync** — Purges local client cache and resynchronizes slash commands."
        ),
        inline=False
    )
    embed.set_footer(text="asukaPot Platform • Zero-tolerance automated protection")
    return embed