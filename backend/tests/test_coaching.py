from datetime import datetime, timedelta, timezone

from tests.conftest import ndjson_lines

NEXT_SESSION_PAYLOAD = {
    "session_focus": "Push — chest emphasis",
    "coaching_note": "Bench moved well at RPE 8 last time; nudge the top set up 2.5kg.",
    "exercises": [
        {
            "exercise_name": "Barbell Bench Press",
            "sets": 4,
            "target_reps": "6–8",
            "target_weight_kg": 102.5,
            "progression_reason": "Last top set was 100kg x 8 @ RPE 8",
            "rpe_target": 8,
        }
    ],
    "deload_recommended": False,
    "deload_reason": None,
}

WEEKLY_PAYLOAD = {
    "headline": "Solid week: bench PR, but legs were neglected.",
    "positives": ["Bench e1RM up 2.1kg"],
    "concerns": ["Quads got 3 sets vs the 12-set minimum"],
    "focus_next_week": "Add one lower-body session.",
    "volume_status": [{"muscle_group": "chest", "status": "optimal"}],
}

PLATEAU_PAYLOAD = {
    "status": "plateaued",
    "trend_summary": "e1RM flat at ~127kg across the last 5 sessions.",
    "recommendation": "Run 5x5 at 90% of current working weight for 2 weeks.",
    "urgency": "medium",
}


async def _seed_session(client, exercise_id, days_ago=0, rpe=8, weight=100.0, reps=8):
    started = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    sid = (await client.post("/api/sessions", json={"started_at": started})).json()["id"]
    for n in range(3):
        await client.post(
            f"/api/sessions/{sid}/sets",
            json={"exercise_id": exercise_id, "reps": reps, "weight_kg": weight, "rpe": rpe},
        )
    await client.patch(f"/api/sessions/{sid}", json={"rpe": rpe})
    return sid


async def _bench_id(client) -> str:
    resp = await client.get("/api/exercises", params={"q": "Barbell Bench Press"})
    return next(e["id"] for e in resp.json() if e["name"] == "Barbell Bench Press")


async def test_next_session_cache_lifecycle(client, fake_ai):
    fake_ai(NEXT_SESSION_PAYLOAD)

    # Brand-new user: no snapshot yet, default push targets inferred.
    first = (await client.get("/api/coaching/next-session")).json()
    assert first["status"] == "stale"
    assert first["request"]["muscles"] == sorted(["chest", "shoulders", "triceps"])

    # Generate: NDJSON deltas then a validated result. Pin the muscles param so
    # the snapshot request key stays stable for the rest of the test.
    muscles = "chest,shoulders,triceps"
    resp = await client.post(f"/api/coaching/next-session/generate?muscles={muscles}")
    assert resp.status_code == 200
    lines = ndjson_lines(resp.text)
    assert lines[0]["type"] == "delta"
    assert lines[-1]["type"] == "result"
    assert lines[-1]["content"]["session_focus"] == "Push — chest emphasis"

    # Cached now.
    second = (await client.get(f"/api/coaching/next-session?muscles={muscles}")).json()
    assert second["status"] == "fresh"
    assert second["content"]["exercises"][0]["target_weight_kg"] == 102.5

    # Logging a new session invalidates the snapshot...
    bench = await _bench_id(client)
    await _seed_session(client, bench)
    third = (await client.get(f"/api/coaching/next-session?muscles={muscles}")).json()
    assert third["status"] == "stale"
    # ...but the previous content is still offered for instant display.
    assert third["cached_content"]["session_focus"] == "Push — chest emphasis"

    # With no muscles param, inference now targets the least-recently-trained
    # groups, so the push snapshot no longer applies.
    inferred = (await client.get("/api/coaching/next-session")).json()
    assert inferred["status"] == "stale"
    assert inferred["request"]["muscles"] != sorted(["chest", "shoulders", "triceps"])


async def test_explicit_muscles_param(client, fake_ai):
    fake_ai(NEXT_SESSION_PAYLOAD)
    resp = (await client.get("/api/coaching/next-session?muscles=quads,hamstrings")).json()
    assert resp["request"]["muscles"] == ["hamstrings", "quads"]

    bad = await client.get("/api/coaching/next-session?muscles=wings")
    assert bad.status_code == 422


async def test_weekly_review_empty_then_generate(client, fake_ai):
    empty = (await client.get("/api/coaching/weekly-review")).json()
    assert empty["status"] == "empty"

    bench = await _bench_id(client)
    await _seed_session(client, bench)

    stale = (await client.get("/api/coaching/weekly-review")).json()
    assert stale["status"] == "stale"

    fake_ai(WEEKLY_PAYLOAD)
    resp = await client.post("/api/coaching/weekly-review/generate")
    assert ndjson_lines(resp.text)[-1]["content"]["headline"].startswith("Solid week")

    fresh = (await client.get("/api/coaching/weekly-review")).json()
    assert fresh["status"] == "fresh"


async def test_plateau_insufficient_then_alerts(client, fake_ai):
    bench = await _bench_id(client)
    insufficient = (await client.get(f"/api/coaching/plateau/{bench}")).json()
    assert insufficient["status"] == "insufficient_data"

    generate = await client.post(f"/api/coaching/plateau/{bench}/generate")
    assert generate.status_code == 409

    for i in range(4):
        await _seed_session(client, bench, days_ago=21 - i * 5)

    stale = (await client.get(f"/api/coaching/plateau/{bench}")).json()
    assert stale["status"] == "stale"

    fake_ai(PLATEAU_PAYLOAD)
    resp = await client.post(f"/api/coaching/plateau/{bench}/generate")
    assert ndjson_lines(resp.text)[-1]["content"]["status"] == "plateaued"

    # Plateau snapshots stay fresh until 3 new sessions of that exercise.
    fresh = (await client.get(f"/api/coaching/plateau/{bench}")).json()
    assert fresh["status"] == "fresh"
    await _seed_session(client, bench, days_ago=1)
    assert (await client.get(f"/api/coaching/plateau/{bench}")).json()["status"] == "fresh"

    alerts = (await client.get("/api/coaching/plateau-alerts")).json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["exercise_name"] == "Barbell Bench Press"
    assert alerts[0]["status"] == "plateaued"


async def test_deload_insufficient_then_generate(client, fake_ai):
    insufficient = (await client.get("/api/coaching/deload-check")).json()
    assert insufficient["status"] == "insufficient_data"

    bench = await _bench_id(client)
    for days_ago in (16, 12, 8, 4, 1):
        await _seed_session(client, bench, days_ago=days_ago, rpe=9)

    stale = (await client.get("/api/coaching/deload-check")).json()
    assert stale["status"] == "stale"

    fake_ai(
        {
            "deload_needed": True,
            "confidence": "high",
            "rationale": "Average RPE 9 across three straight weeks.",
            "deload_type": "volume",
            "deload_protocol": "50% of normal volume for 5–7 days, same weights.",
        }
    )
    resp = await client.post("/api/coaching/deload-check/generate")
    result = ndjson_lines(resp.text)[-1]
    assert result["content"]["deload_needed"] is True
    assert (await client.get("/api/coaching/deload-check")).json()["status"] == "fresh"
