import os
import asyncio
import logging
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from keep_alive import start_web_server
from database.core import init_database
from utils.ui import HoneypotPersistentView
from utils.db_sync import restore_database_from_discord, backup_database_to_discord
from config import DISCORD_TOKEN, DEV_GUILD_ID, BOT_ACTIVITY_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Core.Master")

INTENTS = discord.Intents.default()
INTENTS.guilds = True
INTENTS.messages = True
INTENTS.message_content = True
INTENTS.members = True

EXTENSIONS = [
    "cogs.trap_listener",
    "cogs.antispike",
    "cogs.stats_and_logs",
    "cogs.admin_panel"
]

class HoneypotBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=INTENTS,
            help_command=None
        )

    async def setup_hook(self):
        # 1. Start HTTP health check server for Render & UptimeRobot
        await start_web_server()

        # 2. Restore database from private Discord channel before loading DB tables
        await restore_database_from_discord(self)

        # 3. Initialize SQLite tables and indexes
        await init_database()

        # 4. Register persistent button view across reboots
        self.add_view(HoneypotPersistentView())

        # 5. Load feature cogs
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                logger.info(f"Loaded extension: {ext}")
            except Exception as e:
                logger.error(f"Failed to load extension {ext}: {e}", exc_info=True)

        # 6. Slash command sync (prevents duplicate command preview bug)
        if DEV_GUILD_ID:
            dev_guild = discord.Object(id=DEV_GUILD_ID)
            self.tree.clear_commands(guild=dev_guild)
            await self.tree.sync(guild=dev_guild)
            logger.info(f"Development mode: Cleaned guild cache for {DEV_GUILD_ID}.")

        synced = await self.tree.sync()
        logger.info(f"Global sync complete: {len(synced)} slash commands registered.")

        # 7. Start automated cloud backup loop (runs every 15 minutes)
        if not self.backup_task.is_running():
            self.backup_task.start()

    @tasks.loop(minutes=15)
    async def backup_task(self):
        """Periodically syncs database to your private Discord channel."""
        await backup_database_to_discord(self)

    @backup_task.before_loop
    async def before_backup(self):
        await self.wait_until_ready()

    async def on_honeypot_trigger(self, guild: discord.Guild, member: discord.Member, action: str, content: str):
        """Immediately syncs the database after an intruder is caught."""
        await backup_database_to_discord(self)

    async def on_ready(self):
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        await self.change_presence(
            activity=discord.CustomActivity(name=BOT_ACTIVITY_NAME),
            status=discord.Status.online
        )

bot = HoneypotBot()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.critical("No DISCORD_TOKEN found in .env file! Exiting.")
        exit(1)
    bot.run(DISCORD_TOKEN)