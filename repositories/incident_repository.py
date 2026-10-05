import json
import aiosqlite
import datetime
from typing import List, Optional, Dict, Any
from config import DB_PATH
from models.incident import Incident, IncidentSeverity, IncidentStatus

class IncidentRepository:
    """Persistence repository for incident triage, evidence, and audit logs."""

    async def create_incident(self, incident: Incident) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO incidents (
                    incident_id, guild_id, user_id, user_name, severity, 
                    status, title, summary, risk_score, correlation_id, 
                    evidence, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                incident.incident_id,
                incident.guild_id,
                incident.user_id,
                incident.user_name,
                incident.severity.value,
                incident.status.value,
                incident.title,
                incident.summary,
                incident.risk_score,
                incident.correlation_id,
                json.dumps(incident.evidence, default=str),
                json.dumps(incident.notes),
                incident.created_at.isoformat()
            ))
            # Write to legacy table for backwards compatibility with existing log queries
            await db.execute("""
                INSERT INTO incident_logs (guild_id, user_id, user_name, action_taken, message_content)
                VALUES (?, ?, ?, ?, ?);
            """, (
                incident.guild_id,
                incident.user_id,
                incident.user_name,
                incident.severity.value,
                incident.evidence.get("raw_content", "")[:1500]
            ))
            await db.commit()

    async def get_incident(self, incident_id: str) -> Optional[Incident]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                return self._row_to_model(dict(row))

    async def resolve_incident(self, incident_id: str, note: str, status: IncidentStatus = IncidentStatus.RESOLVED) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT notes FROM incidents WHERE incident_id = ?", (incident_id,)) as cur:
                row = await cur.fetchone()
                if not row:
                    return False
                notes: List[str] = json.loads(row["notes"])
                notes.append(f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}: {note}")

            await db.execute("""
                UPDATE incidents 
                SET status = ?, notes = ?, resolved_at = ?
                WHERE incident_id = ?;
            """, (
                status.value,
                json.dumps(notes),
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                incident_id
            ))
            await db.commit()
            return True

    async def get_guild_incidents(self, guild_id: int, limit: int = 5) -> List[Incident]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM incidents WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?", 
                (guild_id, limit)
            ) as cur:
                rows = await cur.fetchall()
                return [self._row_to_model(dict(r)) for r in rows]

    async def purge_old_incidents(self, days_retention: int = 90) -> int:
        """Enforces data retention policy by clearing resolved telemetry older than N days."""
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_retention)).isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM incidents WHERE status IN ('RESOLVED', 'FALSE_POSITIVE') AND created_at < ?",
                (cutoff,)
            )
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    def _row_to_model(self, data: Dict[str, Any]) -> Incident:
        return Incident(
            incident_id=data["incident_id"],
            guild_id=data["guild_id"],
            user_id=data["user_id"],
            user_name=data["user_name"],
            severity=IncidentSeverity(data["severity"]),
            status=IncidentStatus(data["status"]),
            title=data["title"],
            summary=data["summary"],
            risk_score=data["risk_score"],
            correlation_id=data["correlation_id"],
            evidence=json.loads(data["evidence"]),
            notes=json.loads(data["notes"]),
            created_at=datetime.datetime.fromisoformat(data["created_at"]),
            resolved_at=datetime.datetime.fromisoformat(data["resolved_at"]) if data["resolved_at"] else None
        )

incident_repo = IncidentRepository()