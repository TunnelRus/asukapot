import json
import aiosqlite
import datetime
from typing import Optional, Dict, Any
from config import DB_PATH
from models.reputation import ActorReputation, EscalationLevel

class ReputationRepository:
    """Manages cross-server behavioral track records and progressive penalties."""

    async def get_or_create(self, user_id: int) -> ActorReputation:
        now = datetime.datetime.now(datetime.timezone.utc)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM actor_reputation WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                if row:
                    return self._row_to_model(dict(row))

            # Create baseline record
            await db.execute("""
                INSERT INTO actor_reputation (user_id, reputation_score, offense_count, first_seen, last_seen, current_escalation, tags)
                VALUES (?, 100, 0, ?, ?, 'NONE', '[]');
            """, (user_id, now.isoformat(), now.isoformat()))
            await db.commit()

            return ActorReputation(
                user_id=user_id,
                reputation_score=100,
                offense_count=0,
                first_seen=now,
                last_seen=now,
                last_offense=None,
                current_escalation=EscalationLevel.NONE,
                tags=[]
            )

    async def record_offense(self, user_id: int, penalty_points: int, tag: str) -> ActorReputation:
        rep = await self.get_or_create(user_id)
        now = datetime.datetime.now(datetime.timezone.utc)

        rep.reputation_score = max(0, rep.reputation_score - penalty_points)
        rep.offense_count += 1
        rep.last_seen = now
        rep.last_offense = now
        if tag not in rep.tags:
            rep.tags.append(tag)
        rep.current_escalation = rep.calculate_escalation()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE actor_reputation 
                SET reputation_score = ?, offense_count = ?, last_seen = ?, 
                    last_offense = ?, current_escalation = ?, tags = ?
                WHERE user_id = ?;
            """, (
                rep.reputation_score,
                rep.offense_count,
                rep.last_seen.isoformat(),
                rep.last_offense.isoformat(),
                rep.current_escalation.value,
                json.dumps(rep.tags),
                user_id
            ))
            await db.commit()
        return rep

    def _row_to_model(self, data: Dict[str, Any]) -> ActorReputation:
        return ActorReputation(
            user_id=data["user_id"],
            reputation_score=data["reputation_score"],
            offense_count=data["offense_count"],
            first_seen=datetime.datetime.fromisoformat(data["first_seen"]),
            last_seen=datetime.datetime.fromisoformat(data["last_seen"]),
            last_offense=datetime.datetime.fromisoformat(data["last_offense"]) if data["last_offense"] else None,
            current_escalation=EscalationLevel(data["current_escalation"]),
            tags=json.loads(data["tags"])
        )

reputation_repo = ReputationRepository()