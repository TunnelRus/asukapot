import time
from collections import defaultdict
import discord
from config import ALERT_COOLDOWN_SECONDS

class AlertManager:
    """Manages alert delivery, deduplication, and alert fatigue mitigation."""

    def __init__(self, cooldown: int = ALERT_COOLDOWN_SECONDS):
        self.cooldown = cooldown
        self._last_alert_time: dict[str, float] = {}

    def should_dispatch(self, guild_id: int, alert_key: str) -> bool:
        key = f"{guild_id}:{alert_key}"
        now = time.time()
        last = self._last_alert_time.get(key, 0.0)

        if now - last < self.cooldown:
            return False

        self._last_alert_time[key] = now
        return True

alert_manager = AlertManager()