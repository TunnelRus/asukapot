import aiosqlite
from typing import Optional, Dict, Any, List, Set, Tuple
from database.core import DB_PATH

async def get_guild_settings(guild_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def upsert_trap_config(guild_id: int, channel_id: int, message_id: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, trap_channel_id, trap_message_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                trap_channel_id = excluded.trap_channel_id,
                trap_message_id = excluded.trap_message_id;
        """, (guild_id, channel_id, message_id))
        await db.commit()

async def disarm_trap(guild_id: int) -> Tuple[int, int]:
    """
    Disarms the honeypot for a guild.
    Returns the old channel_id and message_id so the bot can clean them up.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT trap_channel_id, trap_message_id FROM guild_settings WHERE guild_id = ?", 
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            old_channel_id = row[0] if row else 0
            old_message_id = row[1] if row else 0

        await db.execute("""
            UPDATE guild_settings 
            SET trap_channel_id = 0, trap_message_id = 0 
            WHERE guild_id = ?;
        """, (guild_id,))
        await db.commit()

        return old_channel_id, old_message_id

async def update_punishment(guild_id: int, action: str, cleanup_hours: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, action, cleanup_hours)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                action = excluded.action,
                cleanup_hours = excluded.cleanup_hours;
        """, (guild_id, action.lower(), cleanup_hours))
        await db.commit()

async def update_log_channel(guild_id: int, log_channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_settings (guild_id, log_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                log_channel_id = excluded.log_channel_id;
        """, (guild_id, log_channel_id))
        await db.commit()

async def increment_catches(guild_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE guild_settings
            SET total_catches = total_catches + 1
            WHERE guild_id = ?;
        """, (guild_id,))
        await db.commit()

        async with db.execute("SELECT total_catches FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 1

async def record_incident_log(guild_id: int, user_id: int, user_name: str, action: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO incident_logs (guild_id, user_id, user_name, action_taken, message_content)
            VALUES (?, ?, ?, ?, ?);
        """, (guild_id, user_id, user_name, action, content[:1500]))
        await db.commit()

async def get_recent_incidents(guild_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM incident_logs WHERE guild_id = ? ORDER BY caught_at DESC LIMIT ?", 
            (guild_id, limit)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def add_whitelist(guild_id: int, target_id: int, target_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO guild_whitelist (guild_id, target_id, target_type)
            VALUES (?, ?, ?);
        """, (guild_id, target_id, target_type))
        await db.commit()

async def remove_whitelist(guild_id: int, target_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM guild_whitelist WHERE guild_id = ? AND target_id = ?", (guild_id, target_id))
        await db.commit()

async def get_guild_whitelist(guild_id: int) -> Set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT target_id FROM guild_whitelist WHERE guild_id = ?", (guild_id,)) as cur:
            rows = await cur.fetchall()
            return {r[0] for r in rows}