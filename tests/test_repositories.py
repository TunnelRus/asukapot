import pytest
import random
import aiosqlite
from config import DB_PATH
from repositories.guild_repository import guild_repo
from repositories.reputation_repository import reputation_repo

@pytest.mark.asyncio
async def test_guild_repository_crud():
    # Use random ID so repeated test runs never collide
    guild_id = random.randint(10000000, 99999999)

    await guild_repo.upsert_trap(guild_id, 111, 222)
    settings = await guild_repo.get_settings(guild_id)
    assert settings is not None
    assert settings["trap_channel_id"] == 111

    await guild_repo.set_scenario(guild_id, "canary_leak")
    updated = await guild_repo.get_settings(guild_id)
    assert updated is not None
    assert updated["active_scenario"] == "canary_leak"

    # Cleanup test data
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM guild_settings WHERE guild_id = ?", (guild_id,))
        await db.commit()

@pytest.mark.asyncio
async def test_reputation_escalation():
    # Fresh actor ID per test run
    user_id = random.randint(10000000, 99999999)

    # First offense: count must be 1
    rep1 = await reputation_repo.record_offense(user_id, 40, "SUSPICIOUS")
    assert rep1.offense_count == 1

    # Second offense: count must be 2 and escalate
    rep2 = await reputation_repo.record_offense(user_id, 40, "PHISHING")
    assert rep2.offense_count == 2
    assert rep2.current_escalation.value in ("SOFTBAN", "BAN")

    # Cleanup test data
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM actor_reputation WHERE user_id = ?", (user_id,))
        await db.commit()