import os
from typing import Set
from dotenv import load_dotenv

load_dotenv()

# Discord Authentication & Environment Scopes
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
LOG_MESSAGE_CONTENT: bool = os.getenv("LOG_MESSAGE_CONTENT", "true").lower() == "true"

raw_dev_guild = os.getenv("DEV_GUILD_ID")
DEV_GUILD_ID: int | None = int(raw_dev_guild) if raw_dev_guild and raw_dev_guild.isdigit() else None

raw_backup_chan = os.getenv("BACKUP_CHANNEL_ID")
BACKUP_CHANNEL_ID: int | None = int(raw_backup_chan) if raw_backup_chan and raw_backup_chan.isdigit() else None

# Master Owners (Fallback defaults preserved + dynamic CSV parser)
DEFAULT_OWNERS: Set[int] = {1087038828474282015, 1430949538754990097}
env_owners_raw = os.getenv("OWNER_IDS", "")
if env_owners_raw:
    parsed_owners = {int(x.strip()) for x in env_owners_raw.split(",") if x.strip().isdigit()}
    OWNER_IDS: Set[int] = DEFAULT_OWNERS.union(parsed_owners)
else:
    OWNER_IDS: Set[int] = DEFAULT_OWNERS

# Static UI Assets
BANNER_IMAGE_URL: str = "https://i.imgur.com/Q2xT0Sp.png"
PANIC_AVATAR_URL: str = "https://i.imgur.com/50MJJIw.png"

# Palette Tokens
COLOR_AMBER: int = 0xD99B26
COLOR_CRIMSON: int = 0x990000
COLOR_NEUTRAL: int = 0x2B2D31
COLOR_SUCCESS: int = 0x43B581
COLOR_INFO: int = 0x3498DB

# Activity Presence
BOT_ACTIVITY_NAME: str = "asuka lover"

# File System Paths
DB_PATH: str = "honeypot_system.db"
AUDIT_LOG_PATH: str = os.getenv("SECURITY_AUDIT_LOG", "security_audit.jsonl")

# Threat & Persona Defaults
DEFAULT_TYPING_JITTER_MIN: float = 0.8
DEFAULT_TYPING_JITTER_MAX: float = 2.4
ALERT_COOLDOWN_SECONDS: int = 60
DEFAULT_SCENARIO: str = "decoy_operator"

HUMAN_EXPLANATION_TEXT: str = (
    "**Why does this channel exist?**\n"
    "Spam bots, phishing accounts, and hijacked user accounts join servers and immediately post scam links "
    "into every single channel they can find. They do not read channel names or look at warnings.\n\n"
    "**Why are you told not to type here?**\n"
    "Real members read where they post. There is never any reason to send a message in this channel. "
    "If you type here (even just saying hi or testing it), the bot assumes you are a spam bot or a compromised "
    "account and removes you from the server immediately.\n\n"
    "**What should you do?**\n"
    "Just leave this channel alone and chat in the regular channels."
)