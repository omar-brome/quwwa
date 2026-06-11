from datetime import datetime, timezone


async def _exercise_id(client, name: str) -> str:
    resp = await client.get("/api/exercises", params={"q": name})
    assert resp.status_code == 200
    matches = [e for e in resp.json() if e["name"] == name]
    assert matches, f"{name} not seeded"
    return matches[0]["id"]


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_exercises_seeded(client):
    resp = await client.get("/api/exercises")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 60
    names = {e["name"] for e in body}
    assert "Barbell Bench Press" in names

    resp = await client.get("/api/exercises", params={"q": "bench"})
    assert all("bench" in e["name"].lower() for e in resp.json())

    resp = await client.get("/api/exercises", params={"muscle": "calves"})
    calf_names = {e["name"] for e in resp.json()}
    assert {"Standing Calf Raise", "Seated Calf Raise"} <= calf_names
    assert all("calves" in e["muscle_groups"] for e in resp.json())


async def test_custom_exercise(client):
    resp = await client.post(
        "/api/exercises",
        json={"name": "Zercher Squat", "muscle_groups": ["quads", "core"], "equipment": "barbell"},
    )
    assert resp.status_code == 201
    assert resp.json()["is_custom"] is True

    dup = await client.post("/api/exercises", json={"name": "zercher squat"})
    assert dup.status_code == 409

    bad = await client.post("/api/exercises", json={"name": "X", "muscle_groups": ["wings"]})
    assert bad.status_code == 422


async def test_session_flow(client):
    bench_id = await _exercise_id(client, "Barbell Bench Press")

    resp = await client.post("/api/sessions", json={"bodyweight_kg": 82.5})
    assert resp.status_code == 201
    session = resp.json()
    sid = session["id"]

    # Warmup + two working sets; set_number auto-increments per exercise.
    s1 = await client.post(
        f"/api/sessions/{sid}/sets",
        json={"exercise_id": bench_id, "reps": 10, "weight_kg": 60, "is_warmup": True},
    )
    assert s1.status_code == 201
    assert s1.json()["set_number"] == 1

    s2 = await client.post(
        f"/api/sessions/{sid}/sets",
        json={"exercise_id": bench_id, "reps": 8, "weight_kg": 100, "rpe": 8},
    )
    assert s2.json()["set_number"] == 2
    s3 = await client.post(
        f"/api/sessions/{sid}/sets",
        json={"exercise_id": bench_id, "reps": 6, "weight_kg": 105, "rpe": 9},
    )
    assert s3.json()["set_number"] == 3

    detail = (await client.get(f"/api/sessions/{sid}")).json()
    assert detail["total_sets"] == 3
    assert detail["working_sets"] == 2
    assert detail["total_volume_kg"] == 100 * 8 + 105 * 6
    assert detail["volume_by_muscle"]["chest"] == 2

    # Finish the session.
    patched = await client.patch(
        f"/api/sessions/{sid}",
        json={"ended_at": datetime.now(timezone.utc).isoformat(), "rpe": 8, "notes": "solid"},
    )
    assert patched.status_code == 200
    assert patched.json()["rpe"] == 8

    # Edit + delete a set.
    set_id = s3.json()["id"]
    edited = await client.patch(f"/api/sets/{set_id}", json={"reps": 7})
    assert edited.json()["reps"] == 7
    assert (await client.delete(f"/api/sets/{set_id}")).status_code == 204
    assert (await client.get(f"/api/sessions/{sid}")).json()["total_sets"] == 2

    listing = (await client.get("/api/sessions")).json()
    assert listing["total"] == 1
    assert listing["items"][0]["exercise_names"] == ["Barbell Bench Press"]

    # Last-used weight surfaces on the exercise list for pre-population.
    exercises = (await client.get("/api/exercises", params={"q": "Barbell Bench"})).json()
    bench = next(e for e in exercises if e["id"] == bench_id)
    assert bench["last_weight_kg"] == 100.0


async def test_profile(client):
    resp = await client.get("/api/profile")
    assert resp.status_code == 200
    assert resp.json()["units"] == "kg"

    update = await client.put(
        "/api/profile",
        json={
            "training_goal": "strength",
            "experience": "advanced",
            "training_days": 5,
            "equipment": ["barbell", "dumbbell"],
            "injury_notes": "left shoulder impingement",
            "units": "lbs",
        },
    )
    assert update.status_code == 200
    body = update.json()
    assert body["training_goal"] == "strength"
    assert body["injury_notes"] == "left shoulder impingement"
    assert body["units"] == "lbs"


async def test_weekly_volume(client):
    squat_id = await _exercise_id(client, "Back Squat")
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    for _ in range(3):
        await client.post(
            f"/api/sessions/{sid}/sets",
            json={"exercise_id": squat_id, "reps": 5, "weight_kg": 120},
        )
    resp = await client.get("/api/stats/weekly-volume")
    assert resp.status_code == 200
    muscles = {m["muscle"]: m for m in resp.json()["muscles"]}
    assert muscles["quads"]["sets"] == 3
    assert muscles["quads"]["min_sets"] == 12
    assert muscles["chest"]["sets"] == 0
