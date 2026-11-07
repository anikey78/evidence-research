import asyncio

import httpx
import pytest

from app.config import Settings
from app.safety import moderate, matches_blocked_phrase


def test_builtin_and_custom_phrase_filters_use_word_boundaries() -> None:
    settings = Settings(_env_file=None, blocked_phrases="steal credentials")

    assert matches_blocked_phrase("How to make a bomb", settings)
    assert matches_blocked_phrase("Please steal credentials", settings)
    assert not matches_blocked_phrase("A skillful research answer", settings)


def test_moderation_blocks_flagged_content() -> None:
    settings = Settings(_env_file=None, openai_api_key="unit-test-key")

    async def run_check():
        transport = httpx.MockTransport(
            lambda _: httpx.Response(200, json={"results": [{"flagged": True}]})
        )
        async with httpx.AsyncClient(transport=transport) as client:
            return await moderate("unsafe request", settings, client)

    decision = asyncio.run(run_check())

    assert decision.allowed is False
    assert decision.message


def test_malformed_moderation_response_fails_closed() -> None:
    settings = Settings(_env_file=None, openai_api_key="unit-test-key")

    async def run_check():
        transport = httpx.MockTransport(
            lambda _: httpx.Response(200, json={"results": [{"unexpected": False}]})
        )
        async with httpx.AsyncClient(transport=transport) as client:
            return await moderate("question", settings, client)

    with pytest.raises(ValueError):
        asyncio.run(run_check())
