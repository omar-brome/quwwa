CSV = """date,exercise,weight_kg,reps,rpe,is_warmup,notes
2026-06-01,Barbell Bench Press,60,10,,true,
2026-06-01,Barbell Bench Press,100,8,8,,felt strong
2026-06-01,Barbell Bench Press,100,7,9,,
2026-06-03,Back Squat,140,5,8,,
2026-06-03,Krunkle Press,40,12,7,,unknown exercise
bad-date,Back Squat,100,5,,,
"""


async def test_csv_import(client):
    resp = await client.post(
        "/api/import/csv",
        files={"file": ("history.csv", CSV.encode(), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sessions_created"] == 2
    assert body["sets_created"] == 5
    assert body["exercises_created"] == ["Krunkle Press"]
    assert any("bad-date" in w for w in body["warnings"])

    sessions = (await client.get("/api/sessions")).json()
    assert sessions["total"] == 2
    newest = sessions["items"][0]
    assert newest["started_at"].startswith("2026-06-03")
    assert set(newest["exercise_names"]) == {"Back Squat", "Krunkle Press"}

    # Set numbering grouped per exercise within the session.
    detail = (await client.get(f"/api/sessions/{sessions['items'][1]['id']}")).json()
    bench_sets = [s for s in detail["sets"] if s["exercise_name"] == "Barbell Bench Press"]
    assert [s["set_number"] for s in bench_sets] == [1, 2, 3]
    assert bench_sets[0]["is_warmup"] is True


async def test_csv_missing_columns(client):
    resp = await client.post(
        "/api/import/csv",
        files={"file": ("bad.csv", b"foo,bar\n1,2", "text/csv")},
    )
    assert resp.status_code == 422
