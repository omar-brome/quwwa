from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine, session_factory
from app.routers import (
    coaching,
    exercises,
    importer,
    profile,
    sessions,
    sets,
    stats,
    videos,
)
from app.seed import ensure_default_profile, seed_exercises


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite dev convenience: create the schema in place. Postgres is managed
    # by Alembic migrations (docker-compose runs `alembic upgrade head`).
    if engine.dialect.name == "sqlite":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        await seed_exercises(db)
        await ensure_default_profile(db)
    yield
    await engine.dispose()


app = FastAPI(title="Quwwa API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    exercises.router,
    sessions.router,
    sets.router,
    profile.router,
    stats.router,
    coaching.router,
    importer.router,
    videos.router,
):
    app.include_router(r, prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "ai_configured": bool(get_settings().anthropic_api_key),
        "model": get_settings().anthropic_model,
    }
