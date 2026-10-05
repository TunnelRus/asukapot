"""
asukaPot Natural Threat Intelligence Engine
Examines messages and behavior, outputting clean, human-readable explanations.
"""

import re
import math
import unicodedata
import discord
from typing import List
from models.rules import ThreatEvaluation

HOMOGLYPH_MAP = {
    'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o', 'р': 'p', 'ѕ': 's', 
    'ԁ': 'd', 'ԛ': 'q', 'і': 'i', 'ј': 'j', 'ո': 'n', 'у': 'y'
}

PHISHING_DOMAINS = [
    r"(?i)\b(?:discor[cd]l?|dlscord|disord|discocrd|discorcl)\.(?:com|gift|net|org|xyz|info|app|co)\b",
    r"(?i)\b(?:steamcommun[il]ty|steam-promo|steamcommunitys|steamcomminuty)\.(?:com|ru|gift|store)\b",
    r"(?i)\b(?:nitro-gift|gift-nitro|free-nitro|get-nitro|discord-drop|nitro-drop)\b",
    r"(?i)\b(?:airdrop-eth|claim-eth|meta-airdrop|phantom-claim|trade-offer)\b"
]

SCAM_TEMPLATES = [
    # Tournament vote pitch
    (r"(?i)\b(?:vote\s+for\s+my\s+team|csgo\s+tournament|vote\s+for\s+us|tournament\s+vote|join\s+my\s+roster)\b", 
     "Used a fake tournament vote scam message"),
    
    # Game testing pitch
    (r"(?i)\b(?:test\s+my\s+game|trying\s+to\s+make\s+a\s+game|playtest\s+my\s+game|give\s+feedback\s+on\s+my\s+game|download\s+my\s+game)\b", 
     "Used a game tester pitch (common malware/token logger trick)"),
    
    # Accidental report pitch
    (r"(?i)\b(?:accidentally\s+reported|mistakenly\s+reported|steam\s+admin|pending\s+ban|discord\s+staff\s+told\s+me)\b", 
     "Used the 'I accidentally reported your account' scam script"),
    
    # Giveaway / Nitro pitch
    (r"(?i)\b(?:who\s+is\s+first|gifted\s+you|claim\s+your\s+gift|won\s+a\s+giveaway|free\s+nitro|steam\s+50\$)\b", 
     "Used a free Nitro or gift giveaway bait message"),

    # Telegram redirect
    (r"(?i)\b(?:t\.me/|telegram\s+channel|add\s+me\s+on\s+telegram)\b", 
     "Posted an external Telegram redirect link")
]

TOKEN_PATTERN = r"[A-Za-z0-9_-]{24,28}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,38}"
WEBHOOK_PATTERN = r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+"
INVISIBLE_CHARS = {'\u200b', '\u200c', '\u200d', '\u200e', '\u200f', '\ufeff', '\u00ad', '\u2060', '\u2061', '\u2062', '\u2063'}

class AdvancedThreatEngine:
    def normalize_homoglyphs(self, text: str) -> str:
        normalized = unicodedata.normalize('NFKD', text)
        return "".join([HOMOGLYPH_MAP.get(char, char) for char in normalized])

    def calculate_entropy(self, text: str) -> float:
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

        # 1. Join-to-Trigger Velocity
        if join_tenure < 10.0:
            risk_score += 45
            flags.append(f"Immediate raid trigger: typed in the trap {join_tenure:.1f}s after joining")
        elif join_tenure < 60.0:
            risk_score += 30
            flags.append(f"Typed in the trap {int(join_tenure)}s after joining")
        elif join_tenure < 300.0:
            risk_score += 15
            flags.append("Posted under 5 minutes after joining")

        # 2. Account Age
        if account_age_days == 0:
            risk_score += 30
            flags.append("Brand new account created today")
        elif account_age_days < 7:
            risk_score += 20
            flags.append(f"New account ({account_age_days} days old)")
        elif account_age_days > 730 and join_tenure > 86400:
            flags.append(f"Older profile ({account_age_days // 365}y old, likely a hijacked friend's account)")
            is_compromised = True

        # 3. Avatar Check
        if member.avatar is None:
            risk_score += 10
            flags.append("Using default Discord avatar")

        # 4. Phishing Domains
        for pattern in PHISHING_DOMAINS:
            if re.search(pattern, normalized_content):
                risk_score += 45
                flags.append("Deceptive phishing or fake scam link")
                break

        # 5. Scam Message Templates
        for pattern, reason in SCAM_TEMPLATES:
            if re.search(pattern, normalized_content):
                risk_score += 30
                flags.append(reason)
                break

        # 6. Token Leaks
        if re.search(TOKEN_PATTERN, content):
            risk_score += 60
            flags.append("Posted a base64 Discord account token")
            is_compromised = True

        if re.search(WEBHOOK_PATTERN, content):
            risk_score += 40
            flags.append("Posted a Discord webhook execution link")

        # 7. Invisible Obfuscation Characters
        invisibles = sum(1 for ch in content if ch in INVISIBLE_CHARS)
        if invisibles > 0:
            risk_score += 25
            flags.append(f"Used {invisibles} zero-width obfuscation characters to try to dodge filters")

        # 8. Mass Mention Attempt
        if content.count("@everyone") > 0 or content.count("@here") > 0:
            risk_score += 25
            flags.append("Attempted to ping @everyone or @here")

        risk_score = min(100, max(0, risk_score))

        # Humanized Threat Levels
        if risk_score >= 75:
            verdict = "Critical"
        elif risk_score >= 50:
            verdict = "High"
        elif risk_score >= 25:
            verdict = "Medium"
        else:
            verdict = "Low"

        return ThreatEvaluation(
            score=risk_score,
            verdict=verdict,
            flags=flags if flags else ["Accidental click or curious member"],
            risk_bar=verdict,
            join_delta=f"{join_tenure:.1f}s",
            account_age=f"{account_age_days}d",
            entropy=round(entropy, 2),
            is_compromised=is_compromised
        )

threat_engine = AdvancedThreatEngine()