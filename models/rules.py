from dataclasses import dataclass
from typing import List

@dataclass
class ThreatEvaluation:
    score: int
    verdict: str
    flags: List[str]
    risk_bar: str
    join_delta: str
    account_age: str
    entropy: float
    is_compromised: bool