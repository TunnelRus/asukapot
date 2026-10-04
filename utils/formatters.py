"""
Grammar & Text Formatting Engine
"""

ACTION_PAST_TENSE = {
    "softban": "softbanned",
    "ban": "banned",
    "kick": "kicked",
    "timeout": "timed out"
}

ACTION_DESCRIPTIVE = {
    "softban": "Softbanned (kicked & message history wiped)",
    "ban": "Permanently Banned",
    "kick": "Kicked from server",
    "timeout": "Timed out for 28 days"
}

def format_action_past(action: str) -> str:
    """Converts action names to grammatically correct past tense."""
    cleaned = action.lower().strip()
    return ACTION_PAST_TENSE.get(cleaned, f"{cleaned}ed")

def format_action_descriptive(action: str) -> str:
    """Returns a natural description of the punishment."""
    cleaned = action.lower().strip()
    return ACTION_DESCRIPTIVE.get(cleaned, cleaned.capitalize())