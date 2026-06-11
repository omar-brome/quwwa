import json
import os
from pathlib import Path

# Must be set before any app import: the engine is built at import time.
_TEST_DB = (Path(__file__).parent / "test_quwwa.db").as_posix()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine, session_factory
from app.main import app
from app.seed import ensure_default_profile, seed_exercises
from app.services import claude as claude_service


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        await seed_exercises(db)
        await ensure_default_profile(db)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    # Release pooled aiosqlite connections so the next test's event loop
    # gets fresh ones.
    await engine.dispose()


@pytest.fixture
def fake_ai(monkeypatch):
    """Replace the Claude client with a canned structured response."""

    def install(payload: dict):
        async def fake_stream(prompt, schema):
            text = json.dumps(payload)
            mid = max(1, len(text) // 2)
            yield {"type": "delta", "text": text[:mid]}
            yield {"type": "delta", "text": text[mid:]}
            yield {"type": "result", "content": payload}

        monkeypatch.setattr(claude_service, "stream_structured", fake_stream)

    return install


def ndjson_lines(body: str) -> list[dict]:
    return [json.loads(line) for line in body.strip().splitlines() if line.strip()]
