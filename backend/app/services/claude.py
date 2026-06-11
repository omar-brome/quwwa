"""Streaming Claude client for coaching generation.

Uses the Messages API with structured outputs (output_config.format), so the
response is guaranteed-valid JSON for the given schema — no parse-and-retry.
Text deltas are surfaced as they stream so the UI can render progress.
"""

import json
from collections.abc import AsyncIterator

from anthropic import APIError, AsyncAnthropic

from app.config import get_settings
from app.services.prompts import SYSTEM_PROMPT


class CoachingError(Exception):
    pass


_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise CoachingError("ANTHROPIC_API_KEY is not configured")
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def stream_structured(prompt: str, schema: dict) -> AsyncIterator[dict]:
    """Yields {"type": "delta", "text": ...} events followed by a final
    {"type": "result", "content": <parsed dict>}."""
    settings = get_settings()
    client = _get_client()
    try:
        async with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=settings.coaching_max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        ) as stream:
            async for text in stream.text_stream:
                yield {"type": "delta", "text": text}
            final = await stream.get_final_message()
    except APIError as exc:
        raise CoachingError(f"Claude API error: {exc.message}") from exc

    if final.stop_reason == "max_tokens":
        raise CoachingError("Coaching response was truncated (max_tokens reached)")
    if final.stop_reason == "refusal":
        raise CoachingError("Claude declined to generate this coaching output")

    text = "".join(block.text for block in final.content if block.type == "text")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CoachingError(f"Coaching response was not valid JSON: {exc}") from exc
    yield {"type": "result", "content": parsed}
