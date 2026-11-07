import re
from dataclasses import dataclass

import httpx

from app.config import Settings

API_BASE = "https://api.openai.com/v1"


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    message: str | None = None


async def moderate(text: str, settings: Settings, client: httpx.AsyncClient) -> SafetyDecision:
    """Fail closed when moderation is unavailable; the model never sees unreviewed input."""
    response = await client.post(
        f"{API_BASE}/moderations",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": "omni-moderation-latest", "input": text},
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise ValueError("The moderation provider returned an invalid response.")
    flagged = results[0].get("flagged")
    if not isinstance(flagged, bool):
        raise ValueError("The moderation provider returned an invalid response.")
    if flagged:
        return SafetyDecision(
            allowed=False,
            message=(
                "I can’t help with that request. I can help with safety, prevention, "
                "support, or a non-actionable explanation instead."
            ),
        )
    return SafetyDecision(allowed=True)


def matches_blocked_phrase(text: str, settings: Settings) -> bool:
    normalized = " ".join(text.casefold().split())
    return any(
        re.search(r"(?<!\w)" + re.escape(" ".join(phrase.split())) + r"(?!\w)", normalized)
        for phrase in settings.deny_phrases
    )
