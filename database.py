import aiosqlite
import logging

DB_PATH = "honeypot.db"
logger = logging.getLogger("Database")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                log_channel_id INTEGER,
                action TEXT DEFAULT 'softban',
                counter_message_id INTEGER DEFAULT 0,
                trigger_count INTEGER DEFAULT 0
            )
        """)
        await db.commit()
    logger.info("Database initialized successfully.")

async def get_guild_settings(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
            return await cursor.fetchone()

async def set_honeypot_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id
        """, (guild_id, channel_id))
        await db.commit()

async def set_log_channel(guild_id: int, log_channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, log_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = excluded.log_channel_id
        """, (guild_id, log_channel_id))
        await db.commit()

async def set_punishment_action(guild_id: int, action: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, action)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET action = excluded.action
        """, (guild_id, action.lower()))
        await db.commit()

async def set_counter_message_id(guild_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, counter_message_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET counter_message_id = excluded.counter_message_id
        """, (guild_id, message_id))
        await db.commit()

async def increment_catches(guild_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE guild_settings
            SET trigger_count = trigger_count + 1
            WHERE guild_id = ?
        """, (guild_id,))
        await db.commit()
        
        async with db.execute("SELECT trigger_count FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 1