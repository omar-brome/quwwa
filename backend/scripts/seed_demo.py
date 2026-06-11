"""Seed (or wipe) demo training data — used for README screenshots, or to
explore the app with realistic history before importing your own.

    python scripts/seed_demo.py            # ~4 weeks of sessions + coaching snapshots
    python scripts/seed_demo.py --clean    # delete ALL sessions and coaching snapshots

Needs the API running on http://127.0.0.1:8000. Coaching snapshots are written
directly to the database (there is deliberately no API for that), so
DATABASE_URL must point at the same DB the API uses; defaults to the
docker-compose Postgres.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://quwwa:quwwa@localhost:5433/quwwa"
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.constants import (  # noqa: E402
    DEFAULT_USER_ID,
    SNAPSHOT_NEXT_SESSION,
    SNAPSHOT_PLATEAU,
    SNAPSHOT_WEEKLY_REVIEW,
)
from app.database import session_factory  # noqa: E402
from app.models import CoachingSnapshot  # noqa: E402
from app.schemas import NextSessionPlan, PlateauReport, WeeklyReview  # noqa: E402
from app.services.coaching_data import week_start  # noqa: E402
from app.services.snapshots import save_snapshot  # noqa: E402

API = "http://127.0.0.1:8000/api"

# (days_ago, session_rpe, bodyweight, [(exercise, [(weight, reps, rpe, warmup), ...])])
# The bench story: stalled around 100kg for three weeks → plateau alert.
SESSIONS = [
    # ~3.5 weeks ago
    (23, 8, 83.1, [
        ("Barbell Bench Press", [(60, 10, None, True), (97.5, 8, 8, False), (97.5, 8, 8, False), (97.5, 7, 9, False)]),
        ("Overhead Press", [(45, 8, 8, False), (45, 8, 8, False), (45, 7, 9, False)]),
        ("Cable Pushdown", [(25, 12, 8, False), (25, 12, 8, False)]),
    ]),
    (22, 7, 83.0, [
        ("Deadlift", [(100, 5, None, True), (155, 5, 7, False), (155, 5, 8, False)]),
        ("Barbell Row", [(75, 8, 7, False), (75, 8, 7, False), (75, 8, 8, False)]),
        ("Dumbbell Curl", [(16, 10, 8, False), (16, 10, 8, False)]),
    ]),
    # 2 weeks ago
    (17, 8, 82.8, [
        ("Barbell Bench Press", [(60, 10, None, True), (100, 8, 8, False), (100, 7, 9, False), (100, 7, 9, False)]),
        ("Overhead Press", [(45, 8, 8, False), (47.5, 8, 8, False), (47.5, 7, 9, False)]),
        ("Cable Fly", [(20, 12, 8, False), (20, 12, 8, False)]),
    ]),
    (16, 7, 82.7, [
        ("Deadlift", [(100, 5, None, True), (160, 5, 8, False), (160, 4, 8, False)]),
        ("Lat Pulldown", [(67.5, 10, 8, False), (67.5, 10, 8, False), (67.5, 9, 8, False)]),
        ("Dumbbell Curl", [(16, 10, 8, False), (16, 9, 9, False)]),
    ]),
    (15, 8, 82.7, [
        ("Back Squat", [(60, 8, None, True), (130, 5, 8, False), (130, 5, 8, False), (130, 5, 8, False)]),
        ("Leg Extension", [(60, 12, 8, False), (60, 12, 8, False)]),
        ("Standing Calf Raise", [(85, 12, 8, False), (85, 12, 8, False)]),
    ]),
    # last week
    (10, 8, 82.5, [
        ("Barbell Bench Press", [(60, 10, None, True), (100, 8, 8, False), (100, 7, 9, False), (97.5, 8, 8, False)]),
        ("Overhead Press", [(47.5, 8, 8, False), (47.5, 8, 8, False), (47.5, 8, 9, False)]),
        ("Cable Fly", [(20, 12, 8, False), (20, 12, 8, False)]),
    ]),
    (9, 8, 82.4, [
        ("Deadlift", [(110, 5, None, True), (165, 4, 8, False), (165, 4, 8, False)]),
        ("Barbell Row", [(77.5, 8, 8, False), (77.5, 8, 8, False), (77.5, 8, 8, False)]),
        ("Face Pull", [(25, 15, 7, False), (25, 15, 7, False)]),
    ]),
    (8, 8, 82.4, [
        ("Back Squat", [(60, 8, None, True), (132.5, 5, 8, False), (132.5, 5, 8, False), (132.5, 5, 9, False)]),
        ("Romanian Deadlift", [(110, 8, 8, False), (110, 8, 8, False), (110, 8, 8, False)]),
        ("Standing Calf Raise", [(85, 12, 8, False), (85, 12, 8, False)]),
    ]),
    (7, 9, 82.3, [
        ("Barbell Bench Press", [(60, 10, None, True), (100, 7, 9, False), (100, 6, 9, False), (100, 6, 10, False)]),
        ("Incline Dumbbell Press", [(28, 10, 9, False), (28, 10, 9, False), (28, 9, 9, False)]),
        ("Lateral Raise", [(12, 15, 8, False), (12, 15, 8, False), (12, 15, 8, False)]),
    ]),
    # this week (Mon / Tue / Wed before a Thursday demo day)
    (3, 8, 82.4, [
        ("Barbell Bench Press", [(60, 10, None, True), (100, 8, 8, False), (100, 7, 9, False), (100, 6, 9, False)]),
        ("Overhead Press", [(50, 8, 8, False), (50, 8, 8, False), (50, 7, 9, False)]),
        ("Incline Dumbbell Press", [(30, 10, 8, False), (30, 10, 8, False), (30, 10, 9, False)]),
        ("Cable Pushdown", [(25, 12, 8, False), (25, 12, 8, False), (25, 12, 8, False)]),
    ]),
    (2, 7, 82.2, [
        ("Deadlift", [(110, 5, None, True), (170, 4, 8, False), (175, 3, 8, False)]),
        ("Barbell Row", [(80, 8, 7, False), (80, 8, 7, False), (80, 8, 8, False)]),
        ("Lat Pulldown", [(70, 10, 8, False), (70, 10, 8, False), (70, 10, 8, False)]),
        ("Dumbbell Curl", [(17.5, 10, 8, False), (17.5, 10, 8, False)]),
    ]),
    (1, 9, 82.0, [
        ("Back Squat", [(60, 8, None, True), (135, 5, 8, False), (140, 5, 9, False), (140, 4, 9, False)]),
        ("Leg Press", [(200, 10, 8, False), (200, 10, 8, False)]),
        ("Lying Leg Curl", [(50, 12, 8, False), (50, 12, 8, False)]),
        ("Standing Calf Raise", [(90, 12, 8, False), (90, 12, 8, False)]),
    ]),
]


def seed_sessions(client: httpx.Client, exercise_ids: dict[str, str]) -> list[str]:
    now = datetime.now(timezone.utc)
    ids = []
    for days_ago, rpe, bw, exercises in sorted(SESSIONS, key=lambda s: -s[0]):
        started = (now - timedelta(days=days_ago)).replace(
            hour=16, minute=30, second=0, microsecond=0
        )
        session = client.post(
            f"{API}/sessions",
            json={"started_at": started.isoformat(), "bodyweight_kg": bw},
        ).json()
        for name, sets in exercises:
            for weight, reps, set_rpe, warmup in sets:
                client.post(
                    f"{API}/sessions/{session['id']}/sets",
                    json={
                        "exercise_id": exercise_ids[name],
                        "weight_kg": weight,
                        "reps": reps,
                        "rpe": set_rpe,
                        "is_warmup": warmup,
                    },
                ).raise_for_status()
        client.patch(
            f"{API}/sessions/{session['id']}",
            json={"ended_at": (started + timedelta(minutes=72)).isoformat(), "rpe": rpe},
        ).raise_for_status()
        ids.append(session["id"])
        print(f"  session {started:%Y-%m-%d}: {len(exercises)} exercises")
    return ids


# --- Coaching snapshots: what the AI layer would have produced. Written
# directly so demo screens render without an API key. ---------------------

NEXT_SESSION_PLAN = {
    "session_focus": "Push — bench intensity reset",
    "coaching_note": (
        "Your bench has been pinned at 100kg for three weeks while set RPE crept "
        "from 8 to 10 — adding weight now would just dig the hole deeper. We reset "
        "the bar to 90kg for crisp fives and keep pressing volume moving through "
        "the overhead press, which still has room at RPE 8."
    ),
    "exercises": [
        {
            "exercise_name": "Barbell Bench Press",
            "sets": 5,
            "target_reps": "5",
            "target_weight_kg": 90.0,
            "progression_reason": "≈70% of your 126kg e1RM — speed work to break the 100kg stall",
            "rpe_target": 7,
        },
        {
            "exercise_name": "Overhead Press",
            "sets": 3,
            "target_reps": "6–8",
            "target_weight_kg": 52.5,
            "progression_reason": "Last week's 50kg×8 was RPE 8 — earned a 2.5kg jump",
            "rpe_target": 8,
        },
        {
            "exercise_name": "Incline Dumbbell Press",
            "sets": 3,
            "target_reps": "8–10",
            "target_weight_kg": 30.0,
            "progression_reason": "Hold weight, push all sets to 10 before moving to 32kg",
            "rpe_target": 8,
        },
        {
            "exercise_name": "Cable Fly",
            "sets": 2,
            "target_reps": "12–15",
            "target_weight_kg": 20.0,
            "progression_reason": "Chest is under its 10-set weekly minimum — cheap extra volume",
            "rpe_target": 8,
        },
    ],
    "deload_recommended": False,
    "deload_reason": None,
}

WEEKLY_REVIEW = {
    "headline": "Squat and deadlift are flying — the bench is the only thing standing still.",
    "positives": [
        "Squat e1RM up ~9kg to 163kg (140×5 @ RPE 9 on Wednesday)",
        "Deadlift moved to 175×3 @ RPE 8 with bar speed to spare",
        "Three for three on planned sessions so far this week",
    ],
    "concerns": [
        "Bench e1RM flat at ~126kg for three straight weeks, RPE rising",
        "Wednesday legs averaged RPE 9 — keep an eye on recovery",
    ],
    "focus_next_week": "Run the bench intensity reset before adding any pressing volume.",
    "volume_status": [
        {"muscle_group": "chest", "status": "under"},
        {"muscle_group": "back", "status": "optimal"},
        {"muscle_group": "quads", "status": "optimal"},
        {"muscle_group": "shoulders", "status": "under"},
    ],
}

PLATEAU_BENCH = {
    "status": "plateaued",
    "trend_summary": (
        "Bench e1RM has oscillated between 123 and 127kg across the last five "
        "sessions while top-set RPE climbed from 8 to 10."
    ),
    "recommendation": (
        "Reset to 90kg (≈70% e1RM) for 5×5 at RPE 7 for two weeks, then rebuild "
        "in 2.5kg jumps — you should pass 100kg with bar speed inside a month."
    ),
    "urgency": "medium",
}


async def write_snapshots(session_ids: list[str], requests: dict) -> None:
    async with session_factory() as db:
        save_snapshot(
            db, DEFAULT_USER_ID, SNAPSHOT_NEXT_SESSION,
            NextSessionPlan.model_validate(NEXT_SESSION_PLAN).model_dump(mode="json"),
            requests["auto"], session_ids[-4:],
        )
        save_snapshot(
            db, DEFAULT_USER_ID, SNAPSHOT_NEXT_SESSION,
            NextSessionPlan.model_validate(NEXT_SESSION_PLAN).model_dump(mode="json"),
            {"muscles": ["chest", "shoulders", "triceps"]}, session_ids[-4:],
        )
        save_snapshot(
            db, DEFAULT_USER_ID, SNAPSHOT_WEEKLY_REVIEW,
            WeeklyReview.model_validate(WEEKLY_REVIEW).model_dump(mode="json"),
            {"week_start": week_start(datetime.now(timezone.utc)).strftime("%Y-%m-%d")},
            session_ids[-3:],
        )
        save_snapshot(
            db, DEFAULT_USER_ID, SNAPSHOT_PLATEAU,
            PlateauReport.model_validate(PLATEAU_BENCH).model_dump(mode="json"),
            {"exercise_id": requests["bench_id"]}, session_ids,
        )
        await db.commit()


async def clean_snapshots() -> None:
    from sqlalchemy import delete

    async with session_factory() as db:
        await db.execute(delete(CoachingSnapshot))
        await db.commit()


def main() -> None:
    clean = "--clean" in sys.argv
    client = httpx.Client(timeout=30)

    if clean:
        while True:
            items = client.get(f"{API}/sessions?limit=100").json()["items"]
            if not items:
                break
            for s in items:
                client.delete(f"{API}/sessions/{s['id']}")
        asyncio.run(clean_snapshots())
        print("Removed all sessions and coaching snapshots.")
        return

    exercises = client.get(f"{API}/exercises").json()
    exercise_ids = {e["name"]: e["id"] for e in exercises}
    print("Seeding demo sessions…")
    session_ids = seed_sessions(client, exercise_ids)

    # The Auto coaching request targets the three least-recently-trained
    # muscles; resolve it from the API so the snapshot matches exactly.
    auto_request = client.get(f"{API}/coaching/next-session").json()["request"]
    asyncio.run(
        write_snapshots(
            session_ids,
            {"auto": auto_request, "bench_id": exercise_ids["Barbell Bench Press"]},
        )
    )

    status = client.get(f"{API}/coaching/next-session").json()["status"]
    print(f"Snapshots written; next-session (Auto) status: {status}")
    assert status == "fresh", "expected the seeded snapshot to be served as fresh"
    print(f"Done: {len(session_ids)} sessions.")


if __name__ == "__main__":
    main()
