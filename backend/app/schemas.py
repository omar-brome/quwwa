from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Exercises


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    muscle_groups: list[str] = []
    category: str | None = None
    equipment: str | None = None


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    muscle_groups: list[str]
    category: str | None
    equipment: str | None
    is_custom: bool
    # Populated by list endpoint for picker UX / weight pre-population.
    last_used_at: datetime | None = None
    last_weight_kg: float | None = None
    last_reps: int | None = None


# ---------------------------------------------------------------------------
# Sessions & sets


class SessionCreate(BaseModel):
    started_at: datetime | None = None
    bodyweight_kg: float | None = Field(default=None, ge=20, le=400)


class SessionPatch(BaseModel):
    ended_at: datetime | None = None
    notes: str | None = None
    rpe: int | None = Field(default=None, ge=1, le=10)
    bodyweight_kg: float | None = Field(default=None, ge=20, le=400)


class SetCreate(BaseModel):
    exercise_id: UUID
    set_number: int | None = Field(default=None, ge=1)
    reps: int | None = Field(default=None, ge=0, le=200)
    weight_kg: float | None = Field(default=None, ge=0, le=2000)
    rpe: int | None = Field(default=None, ge=1, le=10)
    is_warmup: bool = False
    notes: str | None = None


class SetPatch(BaseModel):
    reps: int | None = Field(default=None, ge=0, le=200)
    weight_kg: float | None = Field(default=None, ge=0, le=2000)
    rpe: int | None = Field(default=None, ge=1, le=10)
    is_warmup: bool | None = None
    notes: str | None = None


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    exercise_id: UUID
    exercise_name: str
    muscle_groups: list[str]
    set_number: int
    reps: int | None
    weight_kg: float | None
    rpe: int | None
    is_warmup: bool
    notes: str | None
    logged_at: datetime


class SessionSummary(BaseModel):
    id: UUID
    started_at: datetime
    ended_at: datetime | None
    rpe: int | None
    notes: str | None
    bodyweight_kg: float | None
    total_sets: int
    working_sets: int
    total_volume_kg: float
    exercise_names: list[str]
    muscle_groups: list[str]


class SessionDetail(SessionSummary):
    sets: list[SetOut]
    volume_by_muscle: dict[str, int]


class SessionListOut(BaseModel):
    items: list[SessionSummary]
    total: int


# ---------------------------------------------------------------------------
# Profile


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    training_goal: str
    experience: str
    training_days: int
    equipment: list[str]
    injury_notes: str | None
    units: str


class ProfileUpdate(BaseModel):
    training_goal: Literal["strength", "hypertrophy", "recomp", "endurance"]
    experience: Literal["beginner", "intermediate", "advanced"]
    training_days: int = Field(ge=1, le=7)
    equipment: list[str]
    injury_notes: str | None = None
    units: Literal["kg", "lbs"]


# ---------------------------------------------------------------------------
# Exercise history / stats


class HistorySet(BaseModel):
    set_number: int
    reps: int | None
    weight_kg: float | None
    rpe: int | None
    is_warmup: bool


class HistorySession(BaseModel):
    session_id: UUID
    date: datetime
    sets: list[HistorySet]
    best_e1rm: float | None


class ExerciseHistoryOut(BaseModel):
    exercise: ExerciseOut
    sessions: list[HistorySession]


class MuscleVolume(BaseModel):
    muscle: str
    sets: int
    min_sets: int | None
    max_sets: int | None


class WeeklyVolumeOut(BaseModel):
    week_start: datetime
    muscles: list[MuscleVolume]


# ---------------------------------------------------------------------------
# AI coaching outputs (validated against Claude's structured output)


class PlannedExercise(BaseModel):
    exercise_name: str
    sets: int
    target_reps: str
    target_weight_kg: float
    progression_reason: str
    rpe_target: float


class NextSessionPlan(BaseModel):
    session_focus: str
    coaching_note: str
    exercises: list[PlannedExercise]
    deload_recommended: bool
    deload_reason: str | None = None


class PlateauReport(BaseModel):
    status: Literal["progressing", "plateaued", "regressing", "fatigued"]
    trend_summary: str
    recommendation: str
    urgency: Literal["low", "medium", "high"]


class MuscleVolumeStatus(BaseModel):
    muscle_group: str
    status: Literal["under", "optimal", "over"]


class WeeklyReview(BaseModel):
    headline: str
    positives: list[str]
    concerns: list[str]
    focus_next_week: str
    volume_status: list[MuscleVolumeStatus]


class DeloadAdvice(BaseModel):
    deload_needed: bool
    confidence: Literal["low", "medium", "high"]
    rationale: str
    deload_type: Literal["full", "volume", "intensity"] | None = None
    deload_protocol: str | None = None


# ---------------------------------------------------------------------------
# Form videos (YouTube search)


class VideoResult(BaseModel):
    video_id: str
    title: str
    channel: str | None = None
    duration: str | None = None
    thumbnail_url: str


class VideoSearchOut(BaseModel):
    items: list[VideoResult]
    source: Literal["api", "scrape", "cache"]


# ---------------------------------------------------------------------------
# CSV import


class ImportResult(BaseModel):
    sessions_created: int
    sets_created: int
    exercises_created: list[str]
    warnings: list[str]
