import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.dbtypes import GUID, JSONDict, StringList


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    muscle_groups: Mapped[list[str]] = mapped_column(StringList(), default=list)
    category: Mapped[str | None] = mapped_column(Text)  # compound | isolation | cardio
    equipment: Mapped[str | None] = mapped_column(Text)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())


class WorkoutSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("rpe BETWEEN 1 AND 10", name="ck_sessions_rpe"),
        Index("ix_sessions_user_started", "user_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    rpe: Mapped[int | None] = mapped_column(Integer)
    bodyweight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))

    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.logged_at",
        lazy="selectin",
    )


class WorkoutSet(Base):
    __tablename__ = "sets"
    __table_args__ = (
        CheckConstraint("rpe BETWEEN 1 AND 10", name="ck_sets_rpe"),
        Index("ix_sets_session", "session_id"),
        Index("ix_sets_exercise", "exercise_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exercises.id"), nullable=False
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    rpe: Mapped[int | None] = mapped_column(Integer)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Both eager: sets are always rendered with their exercise, and ownership
    # checks need the parent session — lazy loads would raise in async context.
    session: Mapped[WorkoutSession] = relationship(back_populates="sets", lazy="joined")
    exercise: Mapped[Exercise] = relationship(lazy="joined")


class CoachingSnapshot(Base):
    __tablename__ = "coaching_snapshots"
    __table_args__ = (
        Index("ix_snapshots_user_type_generated", "user_id", "snapshot_type", "generated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    snapshot_type: Mapped[str] = mapped_column(Text, nullable=False)
    # {"data": <validated AI output>, "request": <params the snapshot answers>}
    content: Mapped[dict] = mapped_column(JSONDict(), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    based_on_sessions: Mapped[list[str]] = mapped_column(StringList(), default=list)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True)
    training_goal: Mapped[str] = mapped_column(Text, default="hypertrophy")
    experience: Mapped[str] = mapped_column(Text, default="intermediate")
    training_days: Mapped[int] = mapped_column(Integer, default=4)
    equipment: Mapped[list[str]] = mapped_column(StringList(), default=list)
    injury_notes: Mapped[str | None] = mapped_column(Text)
    units: Mapped[str] = mapped_column(Text, default="kg")
