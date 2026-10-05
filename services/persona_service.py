import asyncio
import random
import discord
from config import DEFAULT_TYPING_JITTER_MIN, DEFAULT_TYPING_JITTER_MAX

class PersonaService:
    """Simulates realistic human operator presence and decoy behavior."""

    async def execute_scenario(self, scenario_name: str, channel: discord.TextChannel, member: discord.Member) -> None:
        scenario = scenario_name.lower().strip()

        if scenario == "decoy_operator":
            # Natural operator jitter (breaks instant-bot fingerprinting)
            jitter = random.uniform(DEFAULT_TYPING_JITTER_MIN, DEFAULT_TYPING_JITTER_MAX)
            async with channel.typing():
                await asyncio.sleep(jitter)

        elif scenario == "canary_leak":
            # Drops a decoy verification error before executing the purge
            fake_notice = await channel.send(
                f"⚠️ `{member.name}`: Session synchronization mismatch. Verifying handshake credentials...",
                delete_after=2.0
            )
            await asyncio.sleep(1.2)

        elif scenario == "silent":
            # Immediate containment without operational signaling
            pass

persona_service = PersonaService()