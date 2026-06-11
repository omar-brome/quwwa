"""Initial schema: exercises, sessions, sets, coaching_snapshots, user_profiles.

Revision ID: 0001
Revises:
Create Date: 2026-06-11

Uses the app's cross-dialect types (GUID / StringList / JSONDict) so the same
migration produces UUID/TEXT[]/JSONB on Postgres and portable types on SQLite.
"""

import sqlalchemy as sa
from alembic import op

from app.dbtypes import GUID, JSONDict, StringList

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("muscle_groups", StringList(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("equipment", sa.Text(), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False),
        sa.Column("created_by", GUID(), nullable=True),
    )

    op.create_table(
        "sessions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("rpe", sa.Integer(), nullable=True),
        sa.Column("bodyweight_kg", sa.Numeric(5, 1), nullable=True),
        sa.CheckConstraint("rpe BETWEEN 1 AND 10", name="ck_sessions_rpe"),
    )
    op.create_index("ix_sessions_user_started", "sessions", ["user_id", "started_at"])

    op.create_table(
        "sets",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "session_id",
            GUID(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exercise_id", GUID(), sa.ForeignKey("exercises.id"), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("rpe", sa.Integer(), nullable=True),
        sa.Column("is_warmup", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rpe BETWEEN 1 AND 10", name="ck_sets_rpe"),
    )
    op.create_index("ix_sets_session", "sets", ["session_id"])
    op.create_index("ix_sets_exercise", "sets", ["exercise_id"])

    op.create_table(
        "coaching_snapshots",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("snapshot_type", sa.Text(), nullable=False),
        sa.Column("content", JSONDict(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("based_on_sessions", StringList(), nullable=False),
    )
    op.create_index(
        "ix_snapshots_user_type_generated",
        "coaching_snapshots",
        ["user_id", "snapshot_type", "generated_at"],
    )

    op.create_table(
        "user_profiles",
        sa.Column("user_id", GUID(), primary_key=True),
        sa.Column("training_goal", sa.Text(), nullable=False),
        sa.Column("experience", sa.Text(), nullable=False),
        sa.Column("training_days", sa.Integer(), nullable=False),
        sa.Column("equipment", StringList(), nullable=False),
        sa.Column("injury_notes", sa.Text(), nullable=True),
        sa.Column("units", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
    op.drop_index("ix_snapshots_user_type_generated", table_name="coaching_snapshots")
    op.drop_table("coaching_snapshots")
    op.drop_index("ix_sets_exercise", table_name="sets")
    op.drop_index("ix_sets_session", table_name="sets")
    op.drop_table("sets")
    op.drop_index("ix_sessions_user_started", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("exercises")
