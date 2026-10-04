import aiosqlite
import logging

DB_PATH = "honeypot_system.db"
logger = logging.getLogger("Database.Core")

async def init_database():
    """Initializes tables, creates indexes, and handles schema setup."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Guild settings
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                trap_channel_id INTEGER DEFAULT 0,
                log_channel_id INTEGER DEFAULT 0,
                action TEXT DEFAULT 'softban',
                cleanup_hours INTEGER DEFAULT 1,
                trap_message_id INTEGER DEFAULT 0,
                total_catches INTEGER DEFAULT 0,
                antispike_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Mod incident logs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS incident_logs (
                incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                action_taken TEXT,
                message_content TEXT,
                caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Whitelist table for immune roles and users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_whitelist (
                guild_id INTEGER,
                target_id INTEGER,
                target_type TEXT, -- 'role' or 'user'
                PRIMARY KEY (guild_id, target_id)
            );
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_incidents_guild ON incident_logs(guild_id);")
        await db.commit()
    logger.info("Database schema initialized.")