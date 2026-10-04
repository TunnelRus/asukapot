import os
from dotenv import load_dotenv

load_dotenv()

# Environment Variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LOG_MESSAGE_CONTENT = os.getenv("LOG_MESSAGE_CONTENT", "true").lower() == "true"

raw_dev_guild = os.getenv("DEV_GUILD_ID")
DEV_GUILD_ID = int(raw_dev_guild) if raw_dev_guild and raw_dev_guild.isdigit() else None

# Cloud Database Backup Channel ID (Private channel in your Discord server)
raw_backup_chan = os.getenv("BACKUP_CHANNEL_ID")
BACKUP_CHANNEL_ID = int(raw_backup_chan) if raw_backup_chan and raw_backup_chan.isdigit() else None

# Bot Master Owners (Permanent immunity & universal command access)
OWNER_IDS = {1087038828474282015, 1430949538754990097}

# Asset URLs
BANNER_IMAGE_URL = "https://i.imgur.com/Q2xT0Sp.png"
PANIC_AVATAR_URL = "https://i.imgur.com/50MJJIw.png"

# Colors
COLOR_AMBER = 0xD99B26
COLOR_CRIMSON = 0x990000
COLOR_NEUTRAL = 0x2B2D31
COLOR_SUCCESS = 0x43B581

# Status
BOT_ACTIVITY_NAME = "asuka lover"

# Human Explanation for the "What is this?" Button
HUMAN_EXPLANATION_TEXT = (
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