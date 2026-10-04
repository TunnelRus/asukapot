import discord
from typing import Tuple, Optional
import logging
from config import OWNER_IDS

logger = logging.getLogger("Utils.Helpers")

def is_admin_or_owner(interaction: discord.Interaction) -> bool:
    """Checks if the user is a server admin or a bot master owner."""
    if interaction.user.id in OWNER_IDS:
        return True
    if isinstance(interaction.user, discord.Member):
        return interaction.user.guild_permissions.administrator
    return False

def can_punish_member(guild: discord.Guild, target: discord.Member) -> Tuple[bool, str]:
    """Validates role hierarchy and owner immunity."""
    # Permanent owner immunity
    if target.id in OWNER_IDS:
        return False, "Target is a Bot Owner."

    if target.id == guild.owner_id:
        return False, "Target is the Server Owner."

    if guild.me.top_role <= target.top_role:
        return False, "Target has a role higher than or equal to the bot."

    return True, "OK"

def check_bot_channel_permissions(channel: discord.TextChannel) -> Tuple[bool, str]:
    """Validates that the bot has necessary permissions in the trap channel."""
    perms = channel.permissions_for(channel.guild.me)
    missing = []
    
    if not perms.view_channel:
        missing.append("View Channel")
    if not perms.manage_messages:
        missing.append("Manage Messages")
    if not perms.send_messages:
        missing.append("Send Messages")

    if missing:
        return False, f"Missing permissions: {', '.join(missing)}"
    return True, "OK"

def cleanup_hours_to_ban_days(hours: int) -> int:
    """Converts cleanup hours into days for the ban endpoint (0 to 7 days)."""
    if hours <= 0:
        return 0
    days = hours // 24
    if hours % 24 > 0 and days < 7:
        days += 1
    return max(1, min(7, days))

async def create_single_use_invite(guild: discord.Guild) -> Optional[str]:
    """
    Creates a single-use (max_uses=1), 7-day invite so accidentally
    caught users can rejoin after securing their account.
    """
    channels_to_check = []
    if guild.system_channel:
        channels_to_check.append(guild.system_channel)

    channels_to_check.extend([c for c in guild.text_channels if c != guild.system_channel])

    for ch in channels_to_check:
        perms = ch.permissions_for(guild.me)
        if perms.create_instant_invite and perms.view_channel:
            try:
                invite = await ch.create_invite(
                    max_age=604800,  # 7 days
                    max_uses=1,
                    unique=True,
                    reason="Honeypot: 1-use rejoin link for softbanned or kicked user."
                )
                return invite.url
            except discord.DiscordException as e:
                logger.debug(f"Could not create invite in #{ch.name}: {e}")
                continue

    return None