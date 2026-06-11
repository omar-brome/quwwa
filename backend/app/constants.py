from uuid import UUID

# Single-user MVP: every request is implicitly this user. The schema carries
# user_id everywhere so multi-user auth can be added without a migration.
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# Canonical muscle group keys. Exercise seeds and volume math both use these.
MUSCLE_GROUPS = [
    "chest",
    "back",
    "shoulders",
    "biceps",
    "triceps",
    "forearms",
    "quads",
    "hamstrings",
    "glutes",
    "calves",
    "core",
]

# Recommended weekly working-set ranges per muscle group (Israetel MEV/MRV-based).
WEEKLY_SET_TARGETS: dict[str, tuple[int, int]] = {
    "chest": (10, 20),
    "back": (10, 25),
    "quads": (12, 20),
    "hamstrings": (10, 20),
    "shoulders": (16, 22),
    "biceps": (10, 14),
    "triceps": (10, 14),
    "calves": (8, 16),
    "glutes": (8, 16),
    "core": (6, 16),
}

TRAINING_GOALS = ["strength", "hypertrophy", "recomp", "endurance"]
EXPERIENCE_LEVELS = ["beginner", "intermediate", "advanced"]
EQUIPMENT_TYPES = ["barbell", "dumbbell", "cable", "machine", "bodyweight"]

SNAPSHOT_NEXT_SESSION = "next_session"
SNAPSHOT_WEEKLY_REVIEW = "weekly_review"
SNAPSHOT_DELOAD_CHECK = "deload_check"
SNAPSHOT_PLATEAU = "plateau_alert"
