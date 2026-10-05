from typing import Dict, Any, Optional, Set
from repositories.guild_repository import guild_repo

class GuildSettingsCache:
    """Memory cache layer preventing redundant SQLite round-trips on message events."""
    def __init__(self) -> None:
        self._cache: Dict[int, Dict[str, Any]] = {}
        self._whitelists: Dict[int, Set[int]] = {}

    async def get(self, guild_id: int) -> Optional[Dict[str, Any]]:
        if guild_id not in self._cache:
            data = await guild_repo.get_settings(guild_id)
            if data:
                self._cache[guild_id] = data
            return data
        return self._cache[guild_id]

    async def get_whitelist(self, guild_id: int) -> Set[int]:
        if guild_id not in self._whitelists:
            wl = await guild_repo.get_whitelist(guild_id)
            self._whitelists[guild_id] = wl
            return wl
        return self._whitelists[guild_id]

    def invalidate(self, guild_id: int) -> None:
        self._cache.pop(guild_id, None)
        self._whitelists.pop(guild_id, None)

cache = GuildSettingsCache()