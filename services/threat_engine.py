import re
import math
import hashlib
import discord
from typing import List
from models.rules import ThreatEvaluation

PHISHING_DOMAINS = [
    r"(?i)\b(?:discor[cd]l?|dlscord|disord|discocrd|discorcl)\.(?:com|gift|net|org|xyz|info|app|co)\b",
    r"(?i)\b(?:steamcommun[il]ty|steam-promo|steamcommunitys)\.(?:com|ru|gift|store)\b",
    r"(?i)\b(?:nitro-gift|gift-nitro|free-nitro|get-nitro|discord-drop)\b",
    r"(?i)\b(?:airdrop-eth|claim-eth|meta-airdrop|phantom-claim)\b"
]

PHISHING_KEYWORDS = [
    r"(?i)\b(?:free\s+nitro|claim\s+your\s+gift|steam\s+50\$|who\s+is\s+first|gifted\s+you)\b",
    r"(?i)\b(?:trade\s+offer|claim\s+airdrop|free\s+robux|csgo\s+skin)\b"
]

TOKEN_PATTERN = r"[A-Za-z0-9_-]{24,28}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,38}"
WEBHOOK_PATTERN = r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+"
INVISIBLE_CHARS = {'\u200b', '\u200c', '\u200d', '\u200e', '\u200f', '\ufeff', '\u00ad', '\u2060'}

class AdvancedThreatEngine:
    """Analyzes message payloads, actor velocity, and evasion techniques."""

    def calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
        return -sum([p * math.log(p) / math.log(2.0) for p in prob])

    def evaluate(self, member: discord.Member, content: str) -> ThreatEvaluation:
        now = discord.utils.utcnow()
        join_tenure = (now - member.joined_at).total_seconds() if member.joined_at else 999999.0
        account_age_days = (now - member.created_at).days
        entropy = self.calculate_entropy(content)

        risk_score = 0
        flags: List[str] = []
        is_compromised = False

        # 1. Join-to-Action Velocity
        if join_tenure < 10.0:
            risk_score += 45
            flags.append(f"Immediate raid trigger: Posted {join_tenure:.1f}s after joining")
        elif join_tenure < 60.0:
            risk_score += 30
            flags.append(f"Fast trigger: Posted {int(join_tenure)}s after joining")
        elif join_tenure < 300.0:
            risk_score += 15
            flags.append("Posted under 5 minutes from joining")

        # 2. Account Age & Session Tenure
        if account_age_days == 0:
            risk_score += 30
            flags.append("Created today (disposable alt)")
        elif account_age_days < 7:
            risk_score += 20
            flags.append(f"New account ({account_age_days}d old)")
        elif account_age_days > 730 and join_tenure > 86400:
            flags.append(f"Established profile ({account_age_days // 365}y old, session hijack indicator)")
            is_compromised = True

        # 3. Avatar check
        if member.avatar is None:
            risk_score += 10
            flags.append("Default Discord avatar")

        # 4. Pattern matching
        for pattern in PHISHING_DOMAINS:
            if re.search(pattern, content):
                risk_score += 45
                flags.append("Deceptive phishing or typosquat URL detected")
                break

        for pattern in PHISHING_KEYWORDS:
            if re.search(pattern, content):
                risk_score += 25
                flags.append("Phishing lure phrase detected")
                break

        # 5. Token & Webhook leaks
        if re.search(TOKEN_PATTERN, content):
            risk_score += 60
            flags.append("Valid-format Discord authentication token detected")
            is_compromised = True

        if re.search(WEBHOOK_PATTERN, content):
            risk_score += 40
            flags.append("Discord Webhook execution URL detected")

        # 6. Invisible Characters Evasion
        invisibles = sum(1 for ch in content if ch in INVISIBLE_CHARS)
        if invisibles > 0:
            risk_score += 25
            flags.append(f"Contains {invisibles} zero-width obfuscation characters")

        # 7. Mass Mention Attempt
        if content.count("@everyone") > 0 or content.count("@here") > 0:
            risk_score += 25
            flags.append("Attempted global mass mention")

        # Normalize score
        risk_score = min(100, max(0, risk_score))

        if risk_score >= 75:
            verdict = "CRITICAL (Automated Self-Bot)"
        elif risk_score >= 50:
            verdict = "HIGH (Compromised Account)"
        elif risk_score >= 25:
            verdict = "MEDIUM (Suspicious Activity)"
        else:
            verdict = "LOW (Accidental Trigger / Curious Member)"

        filled = int(risk_score / 10)
        empty = 10 - filled
        risk_bar = f"[{'█' * filled}{'░' * empty}] {risk_score}/100"

        return ThreatEvaluation(
            score=risk_score,
            verdict=verdict,
            flags=flags if flags else ["Manual entry without active evasion patterns"],
            risk_bar=risk_bar,
            join_delta=f"{join_tenure:.1f}s",
            account_age=f"{account_age_days}d",
            entropy=round(entropy, 2),
            is_compromised=is_compromised
        )

threat_engine = AdvancedThreatEngine()