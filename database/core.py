import aiosqlite
import logging
from config import DB_PATH

logger = logging.getLogger("Database.Core")

async def init_database() -> None:
    """Executes atomic migrations and builds indexes for high-throughput queries."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA synchronous = NORMAL;")
        await db.execute("PRAGMA foreign_keys = ON;")

        # 1. Base guild settings table
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
                active_scenario TEXT DEFAULT 'decoy_operator',
                auto_escalate INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Automatic schema migration: ensure newer columns exist in older database files
        async with db.execute("PRAGMA table_info(guild_settings)") as cur:
            columns = [row[1] for row in await cur.fetchall()]

        if "active_scenario" not in columns:
            await db.execute("ALTER TABLE guild_settings ADD COLUMN active_scenario TEXT DEFAULT 'decoy_operator';")
            logger.info("Database migration: Added active_scenario column to guild_settings.")

        if "auto_escalate" not in columns:
            await db.execute("ALTER TABLE guild_settings ADD COLUMN auto_escalate INTEGER DEFAULT 1;")
            logger.info("Database migration: Added auto_escalate column to guild_settings.")

        # 2. Legacy incident logs table
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

        # 3. Incident management table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                correlation_id TEXT NOT NULL,
                evidence TEXT DEFAULT '{}',
                notes TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP NULL
            );
        """)

        # 4. Actor reputation tracking table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS actor_reputation (
                user_id INTEGER PRIMARY KEY,
                reputation_score INTEGER DEFAULT 100,
                offense_count INTEGER DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_offense TIMESTAMP NULL,
                current_escalation TEXT DEFAULT 'NONE',
                tags TEXT DEFAULT '[]'
            );
        """)

        # 5. Whitelist table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_whitelist (
                guild_id INTEGER,
                target_id INTEGER,
                target_type TEXT,
                PRIMARY KEY (guild_id, target_id)
            );
        """)

        # Performance Indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_incidents_guild ON incidents(guild_id, status);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_incidents_user ON incidents(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_incidents_corr ON incidents(correlation_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_actor_rep ON actor_reputation(user_id);")

        await db.commit()
    logger.info("Database schema initialized and verified.")