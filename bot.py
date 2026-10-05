import os
import asyncio
import logging
import datetime
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from keep_alive import start_web_server
from database.core import init_database
from utils.ui import HoneypotPersistentView
from utils.db_sync import restore_database_from_discord, backup_database_to_discord
from repositories.incident_repository import incident_repo
from services.fleet_service import fleet_service
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
        self.start_time: datetime.datetime = discord.utils.utcnow()

    async def setup_hook(self):
        # 1. Launch HTTP health-check server for UptimeRobot
        await start_web_server()

        # 2. Cloud DB recovery from Discord private channel
        await restore_database_from_discord(self)

        # 3. Database initialization and migrations
        await init_database()

        # 4. Register UI views
        self.add_view(HoneypotPersistentView())

        # 5. Extension loader
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                logger.info(f"Loaded extension: {ext}")
            except Exception as e:
                logger.error(f"Failed loading extension {ext}: {e}", exc_info=True)

        # 6. Slash sync
        if DEV_GUILD_ID:
            dev_guild = discord.Object(id=DEV_GUILD_ID)
            self.tree.clear_commands(guild=dev_guild)
            await self.tree.sync(guild=dev_guild)
            logger.info(f"Cleaned dev guild tree for {DEV_GUILD_ID}")

        synced = await self.tree.sync()
        logger.info(f"Global sync complete: {len(synced)} commands registered.")

        # 7. Start supervisor loops
        if not self.backup_task.is_running():
            self.backup_task.start()
        if not self.retention_task.is_running():
            self.retention_task.start()

    @tasks.loop(minutes=15)
    async def backup_task(self):
        """Dispatches automated database snapshot to Discord backup channel."""
        await backup_database_to_discord(self)

    @backup_task.before_loop
    async def before_backup(self):
        await self.wait_until_ready()

    @tasks.loop(hours=24)
    async def retention_task(self):
        """Purges resolved incident logs past retention thresholds."""
        purged = await incident_repo.purge_old_incidents(days_retention=90)
        if purged > 0:
            logger.info(f"Automated retention: Purged {purged} expired incidents.")

    @retention_task.before_loop
    async def before_retention(self):
        await self.wait_until_ready()

    async def on_honeypot_trigger(self, guild: discord.Guild, member: discord.Member, action: str, content: str, incident=None):
        """Dispatches cloud snapshot on every trigger."""
        await backup_database_to_discord(self)

    async def on_ready(self):
        if self.user:
            logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        else:
            logger.info("Logged in successfully.")

        await self.change_presence(
            activity=discord.CustomActivity(name=BOT_ACTIVITY_NAME),
            status=discord.Status.online
        )

        # Auto-upgrade all armed honeypots across servers
        await fleet_service.auto_upgrade_fleet(self)

bot = HoneypotBot()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.critical("No DISCORD_TOKEN found in environment! Exiting.")
        exit(1)
    bot.run(DISCORD_TOKEN)