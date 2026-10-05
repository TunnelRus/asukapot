import aiosqlite
from typing import Dict, Any, Optional, Set, Tuple
from config import DB_PATH

class GuildRepository:
    """Manages persistence for guild configuration and whitelist entities."""

    async def get_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def upsert_trap(self, guild_id: int, channel_id: int, message_id: int = 0) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, trap_channel_id, trap_message_id)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET 
                    trap_channel_id = excluded.trap_channel_id,
                    trap_message_id = excluded.trap_message_id;
            """, (guild_id, channel_id, message_id))
            await db.commit()

    async def disarm(self, guild_id: int) -> Tuple[int, int]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT trap_channel_id, trap_message_id FROM guild_settings WHERE guild_id = ?", 
                (guild_id,)
            ) as cur:
                row = await cur.fetchone()
                old_chan = row[0] if row else 0
                old_msg = row[1] if row else 0

            await db.execute("""
                UPDATE guild_settings 
                SET trap_channel_id = 0, trap_message_id = 0 
                WHERE guild_id = ?;
            """, (guild_id,))
            await db.commit()
            return old_chan, old_msg

    async def set_action(self, guild_id: int, action: str, cleanup_hours: int) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, action, cleanup_hours)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET 
                    action = excluded.action,
                    cleanup_hours = excluded.cleanup_hours;
            """, (guild_id, action.lower(), cleanup_hours))
            await db.commit()

    async def set_logs(self, guild_id: int, log_channel_id: int) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, log_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET 
                    log_channel_id = excluded.log_channel_id;
            """, (guild_id, log_channel_id))
            await db.commit()

    async def set_scenario(self, guild_id: int, scenario: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, active_scenario)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET 
                    active_scenario = excluded.active_scenario;
            """, (guild_id, scenario.lower()))
            await db.commit()

    async def increment_catches(self, guild_id: int) -> int:
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

    async def add_whitelist(self, guild_id: int, target_id: int, target_type: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR IGNORE INTO guild_whitelist (guild_id, target_id, target_type)
                VALUES (?, ?, ?);
            """, (guild_id, target_id, target_type))
            await db.commit()

    async def remove_whitelist(self, guild_id: int, target_id: int) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM guild_whitelist WHERE guild_id = ? AND target_id = ?", (guild_id, target_id))
            await db.commit()

    async def get_whitelist(self, guild_id: int) -> Set[int]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT target_id FROM guild_whitelist WHERE guild_id = ?", (guild_id,)) as cur:
                rows = await cur.fetchall()
                return {r[0] for r in rows}

guild_repo = GuildRepository()