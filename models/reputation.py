from dataclasses import dataclass, field
from enum import Enum
import datetime
from typing import List

class EscalationLevel(str, Enum):
    NONE = "NONE"
    WARN = "WARN"
    TIMEOUT = "TIMEOUT"
    SOFTBAN = "SOFTBAN"
    BAN = "BAN"

@dataclass
class ActorReputation:
    user_id: int
    reputation_score: int  # 100 = completely trustworthy, 0 = active threat actor
    offense_count: int
    first_seen: datetime.datetime
    last_seen: datetime.datetime
    last_offense: datetime.datetime | None
    current_escalation: EscalationLevel = EscalationLevel.NONE
    tags: List[str] = field(default_factory=list)

    def calculate_escalation(self) -> EscalationLevel:
        """Determines automated punishment escalation based on cross-server track record."""
        if self.offense_count >= 3 or self.reputation_score <= 15:
            return EscalationLevel.BAN
        elif self.offense_count == 2 or self.reputation_score <= 40:
            return EscalationLevel.SOFTBAN
        elif self.offense_count == 1:
            return EscalationLevel.TIMEOUT
        return EscalationLevel.NONE