import discord
import re

SCAM_PATTERNS = [
    r"(?i)\b(nitro|steam|airdrop|gift|crypto|free\s*nitro|csgo|trade)\b",
    r"(?i)https?://[^\s]+"
]

def analyze_intruder_risk(member: discord.Member, content: str) -> str:
    """
    Evaluates account age, join age, and message content to return 
    a natural, human-readable risk summary for staff logs.
    """
    now = discord.utils.utcnow()
    join_age_seconds = (now - member.joined_at).total_seconds() if member.joined_at else 999999
    account_age_days = (now - member.created_at).days

    reasons = []

    # Joined very recently
    if join_age_seconds < 30:
        reasons.append("Joined under 30 seconds ago (likely automated raid bot)")
    elif join_age_seconds < 180:
        reasons.append("Joined under 3 minutes ago")

    # Account is very new
    if account_age_days < 3:
        reasons.append(f"Brand new account ({account_age_days}d old alt)")
    elif account_age_days > 365 and join_age_seconds > 86400:
        reasons.append("Established account (possible hijacked or compromised user)")

    # Message contains scam phrases or links
    for pattern in SCAM_PATTERNS:
        if re.search(pattern, content):
            reasons.append("Posted known scam keyword or link")
            break

    if not reasons:
        return "Manual misclick or curious member"

    return " • ".join(reasons)