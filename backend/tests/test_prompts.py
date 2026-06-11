from app.models import UserProfile
from app.services.prompts import (
    build_deload_prompt,
    build_next_session_prompt,
    build_plateau_prompt,
    build_weekly_review_prompt,
)


def _profile() -> UserProfile:
    return UserProfile(
        user_id=None,
        training_goal="hypertrophy",
        experience="intermediate",
        training_days=4,
        equipment=["barbell", "dumbbell"],
        injury_notes="left shoulder impingement",
        units="kg",
    )


def test_next_session_prompt_includes_history_and_injuries():
    sessions = [
        {
            "id": "x",
            "date": "2026-06-08",
            "session_rpe": 8,
            "sets": [
                {
                    "exercise_name": "Barbell Bench Press",
                    "muscle_groups": ["chest"],
                    "weight_kg": 100.0,
                    "reps": 8,
                    "rpe": 8,
                    "is_warmup": False,
                },
                {
                    "exercise_name": "Barbell Bench Press",
                    "muscle_groups": ["chest"],
                    "weight_kg": 60.0,
                    "reps": 10,
                    "rpe": None,
                    "is_warmup": True,
                },
            ],
        }
    ]
    e1rms = [{"exercise_name": "Barbell Bench Press", "e1rm_kg": 126.7}]
    prompt = build_next_session_prompt(_profile(), ["chest", "triceps"], sessions, e1rms)
    assert "left shoulder impingement" in prompt
    assert "100kg × 8 reps @ RPE 8" in prompt
    assert "(warmup)" in prompt
    assert "~126.7kg" in prompt
    assert "chest, triceps" in prompt


def test_next_session_prompt_handles_no_history():
    prompt = build_next_session_prompt(_profile(), ["chest"], [], [])
    assert "no logged sessions yet" in prompt.lower()


def test_plateau_prompt_renders_unrated_rpe():
    sessions = [
        {
            "date": f"2026-05-{10 + i:02d}",
            "best_e1rm": 120.0 + i,
            "sets": [
                {"weight_kg": 100.0, "reps": 6, "rpe": None, "is_warmup": False},
            ],
        }
        for i in range(4)
    ]
    prompt = build_plateau_prompt(_profile(), "Back Squat", sessions)
    assert "RPE ?" in prompt
    assert "120.0 → 121.0 → 122.0 → 123.0" in prompt


def test_weekly_and_deload_prompts_render():
    from datetime import datetime, timezone

    weekly = build_weekly_review_prompt(
        _profile(),
        {
            "week_start": datetime(2026, 6, 8, tzinfo=timezone.utc),
            "week_end": datetime(2026, 6, 15, tzinfo=timezone.utc),
            "session_count": 3,
            "total_sets": 42,
            "avg_rpe": None,
            "muscle_volumes": [
                {"muscle": "chest", "sets": 12, "min_sets": 10, "max_sets": 20}
            ],
            "prs": [],
        },
    )
    assert "not rated" in weekly
    assert "3 / 4 planned" in weekly

    deload = build_deload_prompt(
        _profile(),
        {
            "weeks": [
                {
                    "week_number": n,
                    "start": datetime(2026, 5, 25, tzinfo=timezone.utc),
                    "session_count": 4,
                    "avg_rpe": 8.5,
                    "total_sets": 60,
                    "high_rpe_count": 2,
                }
                for n in (1, 2, 3)
            ],
            "rpe_trend": "worsening",
            "bw_trend": "declining",
        },
    )
    assert "worsening" in deload
    assert "Sessions with RPE ≥ 9: 2" in deload
