import os
import json
import logging
import datetime
from typing import Any, Dict
from config import AUDIT_LOG_PATH

class StructuredSecurityLogger:
    """Security event logger outputting machine-readable JSONL audit trails."""
    def __init__(self, log_file: str = AUDIT_LOG_PATH):
        self.log_file = log_file
        self.logger = logging.getLogger("asukaPot.Audit")

    def log_event(
        self,
        event_type: str,
        guild_id: int,
        user_id: int,
        correlation_id: str,
        severity: str,
        details: Dict[str, Any]
    ) -> None:
        payload = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event_type": event_type,
            "guild_id": guild_id,
            "user_id": user_id,
            "correlation_id": correlation_id,
            "severity": severity,
            "details": details
        }
        
        # Write to JSONL
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, default=str) + "\n")
        except Exception as e:
            self.logger.error(f"Failed writing security audit entry: {e}")

        # Human-readable stream log
        self.logger.info(
            f"AUDIT [{severity}] {event_type} | Guild: {guild_id} | User: {user_id} | Corr: {correlation_id}"
        )

security_logger = StructuredSecurityLogger()