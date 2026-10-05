from typing import Optional, Dict, Any, List, Set, Tuple
from repositories.guild_repository import guild_repo
from repositories.incident_repository import incident_repo

async def get_guild_settings(guild_id: int) -> Optional[Dict[str, Any]]:
    return await guild_repo.get_settings(guild_id)

async def upsert_trap_config(guild_id: int, channel_id: int, message_id: int = 0) -> None:
    await guild_repo.upsert_trap(guild_id, channel_id, message_id)

async def disarm_trap(guild_id: int) -> Tuple[int, int]:
    return await guild_repo.disarm(guild_id)

async def update_punishment(guild_id: int, action: str, cleanup_hours: int) -> None:
    await guild_repo.set_action(guild_id, action, cleanup_hours)

async def update_log_channel(guild_id: int, log_channel_id: int) -> None:
    await guild_repo.set_logs(guild_id, log_channel_id)

async def increment_catches(guild_id: int) -> int:
    return await guild_repo.increment_catches(guild_id)

async def add_whitelist(guild_id: int, target_id: int, target_type: str) -> None:
    await guild_repo.add_whitelist(guild_id, target_id, target_type)

async def remove_whitelist(guild_id: int, target_id: int) -> None:
    await guild_repo.remove_whitelist(guild_id, target_id)

async def get_guild_whitelist(guild_id: int) -> Set[int]:
    return await guild_repo.get_whitelist(guild_id)

async def get_recent_incidents(guild_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    incidents = await incident_repo.get_guild_incidents(guild_id, limit)
    return [
        {
            "caught_at": inc.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "user_name": inc.user_name,
            "action_taken": inc.severity.value
        }
        for inc in incidents
    ]