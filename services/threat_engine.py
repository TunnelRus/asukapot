"""
asukaPot Advanced Threat Intelligence Engine
Includes homoglyph normalization, scam template heuristics,
entropy analysis, and zero-width character unmasking.
"""

import re
import math
import unicodedata
import discord
from typing import List
from models.rules import ThreatEvaluation

# Homoglyph normalization map (common Cyrillic & Latin lookalikes used in phishing)
HOMOGLYPH_MAP = {
    'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o', 'р': 'p', 'ѕ': 's', 
    'ԁ': 'd', 'ԛ': 'q', 'і': 'i', 'ј': 'j', 'ո': 'n', 'у': 'y'
}

# Deceptive & Typosquatted Domains
PHISHING_DOMAINS = [
    r"(?i)\b(?:discor[cd]l?|dlscord|disord|discocrd|discorcl)\.(?:com|gift|net|org|xyz|info|app|co)\b",
    r"(?i)\b(?:steamcommun[il]ty|steam-promo|steamcommunitys|steamcomminuty)\.(?:com|ru|gift|store)\b",
    r"(?i)\b(?:nitro-gift|gift-nitro|free-nitro|get-nitro|discord-drop|nitro-drop)\b",
    r"(?i)\b(?:airdrop-eth|claim-eth|meta-airdrop|phantom-claim|trade-offer)\b"
]

# Social Engineering Phishing Templates
SCAM_TEMPLATES = [
    r"(?i)\b(?:vote\s+for\s+my\s+team|csgo\s+tournament|vote\s+for\s+us|tournament\s+vote)\b",
    r"(?i)\b(?:test\s+my\s+game|trying\s+to\s+make\s+a\s+game|playtest\s+my\s+game|give\s+feedback\s+on\s+my\s+game)\b",
    r"(?i)\b(?:who\s+is\s+first|gifted\s+you|claim\s+your\s+gift|won\s+a\s+giveaway)\b",
    r"(?i)\b(?:discord\s+nitro\s+for\s+free|steam\s+50\$|claim\s+airdrop)\b"
]

TOKEN_PATTERN = r"[A-Za-z0-9_-]{24,28}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,38}"
WEBHOOK_PATTERN = r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+"
INVISIBLE_CHARS = {'\u200b', '\u200c', '\u200d', '\u200e', '\u200f', '\ufeff', '\u00ad', '\u2060', '\u2061', '\u2062', '\u2063'}

class AdvancedThreatEngine:
    """Multi-vector heuristic scanner analyzing payloads, velocity, and evasions."""

    def normalize_homoglyphs(self, text: str) -> str:
        """Replaces deceptive lookalike unicode characters with standard ASCII."""
        normalized = unicodedata.normalize('NFKD', text)
        result = []
        for char in normalized:
            result.append(HOMOGLYPH_MAP.get(char, char))
        return "".join(result)

    def calculate_entropy(self, text: str) -> float:
        """Calculates Shannon entropy to detect encrypted payloads, token dumps, or high-randomness text."""
        if not text:
            return 0.0
        prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
        return -sum([p * math.log(p) / math.log(2.0) for p in prob])

    def evaluate(self, member: discord.Member, content: str) -> ThreatEvaluation:
        now = discord.utils.utcnow()
        join_tenure = (now - member.joined_at).total_seconds() if member.joined_at else 999999.0
        account_age_days = (now - member.created_at).days
        
        normalized_content = self.normalize_homoglyphs(content)
        entropy = self.calculate_entropy(content)

        risk_score = 0
        flags: List[str] = []
        is_compromised = False

        # 1. Join-to-Trigger Velocity (Strongest indicator of self-bots)
        if join_tenure < 10.0:
            risk_score += 45
            flags.append(f"Immediate raid trigger: posted {join_tenure:.1f}s after joining")
        elif join_tenure < 60.0:
            risk_score += 30
            flags.append(f"Fast trigger: posted {int(join_tenure)}s after joining")
        elif join_tenure < 300.0:
            risk_score += 15
            flags.append("Posted under 5 minutes from joining")

        # 2. Account Age & Session Tenure
        if account_age_days == 0:
            risk_score += 30
            flags.append("Created today (disposable alt)")
        elif account_age_days < 7:
            risk_score += 20
            flags.append(f"New account ({account_age_days} days old)")
        elif account_age_days > 730 and join_tenure > 86400:
            flags.append(f"Established profile ({account_age_days // 365}y old, probable session hijack)")
            is_compromised = True

        # 3. Avatar Check
        if member.avatar is None:
            risk_score += 10
            flags.append("Default Discord avatar")

        # 4. Homoglyph / Typosquat URL Matching
        for pattern in PHISHING_DOMAINS:
            if re.search(pattern, normalized_content):
                risk_score += 45
                flags.append("Deceptive phishing or typosquatted domain detected")
                break

        # 5. Social Engineering Phrases
        for pattern in SCAM_TEMPLATES:
            if re.search(pattern, normalized_content):
                risk_score += 30
                flags.append("Matches known scam template (tournament vote, game tester, or fake giveaway)")
                break

        # 6. Discord Token & Webhook Leaks
        if re.search(TOKEN_PATTERN, content):
            risk_score += 60
            flags.append("Valid base64 Discord authentication token format detected")
            is_compromised = True

        if re.search(WEBHOOK_PATTERN, content):
            risk_score += 40
            flags.append("Discord webhook execution URL detected")

        # 7. Invisible Obfuscation Characters
        invisibles = sum(1 for ch in content if ch in INVISIBLE_CHARS)
        if invisibles > 0:
            risk_score += 25
            flags.append(f"Contains {invisibles} zero-width obfuscation characters")

        # 8. Mass Mention Attempt
        if content.count("@everyone") > 0 or content.count("@here") > 0:
            risk_score += 25
            flags.append("Attempted global mass notification (@everyone/@here)")

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