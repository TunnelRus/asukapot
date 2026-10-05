from dataclasses import dataclass, field
from enum import Enum
import datetime
from typing import Dict, Any, List

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"

@dataclass
class Incident:
    incident_id: str
    guild_id: int
    user_id: int
    user_name: str
    severity: IncidentSeverity
    status: IncidentStatus
    title: str
    summary: str
    risk_score: int
    correlation_id: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    resolved_at: datetime.datetime | None = None