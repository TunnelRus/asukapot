import pytest
import datetime
from unittest.mock import MagicMock
import discord
from services.threat_engine import threat_engine

@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    member.id = 123456789
    member.name = "TestSubject"
    member.avatar = None
    member.guild = MagicMock()
    member.guild.roles = []
    now = discord.utils.utcnow()
    member.created_at = now
    member.joined_at = now - datetime.timedelta(seconds=4)
    return member

def test_threat_engine_detects_raid_velocity(mock_member):
    eval_res = threat_engine.evaluate(mock_member, "Hello world")
    assert eval_res.score >= 45
    assert any("Immediate raid trigger" in f for f in eval_res.flags)

def test_threat_engine_detects_phishing_link(mock_member):
    eval_res = threat_engine.evaluate(mock_member, "Free nitro here: https://discorcl.gift/drop")
    assert eval_res.score >= 70
    assert any("Deceptive phishing" in f for f in eval_res.flags)
    assert eval_res.verdict.upper().startswith("CRITICAL")

def test_threat_engine_detects_invisible_characters(mock_member):
    payload = "Check\u200bout\u200cthis"
    eval_res = threat_engine.evaluate(mock_member, payload)
    assert any("zero-width obfuscation" in f for f in eval_res.flags)