import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from services.persona_service import persona_service

@pytest.mark.asyncio
async def test_persona_silent_mode():
    channel = MagicMock(spec=discord.TextChannel)
    member = MagicMock(spec=discord.Member)
    await persona_service.execute_scenario("silent", channel, member)
    channel.send.assert_not_called()

@pytest.mark.asyncio
async def test_persona_canary_leak():
    channel = AsyncMock(spec=discord.TextChannel)
    member = MagicMock(spec=discord.Member)
    member.name = "Infiltrator"
    await persona_service.execute_scenario("canary_leak", channel, member)
    channel.send.assert_called_once()