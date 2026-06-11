"""The four coaching prompts plus their structured-output JSON schemas.

Templates follow the product spec wording closely; loops are rendered in
Python instead of a template engine. Every prompt receives Epley-estimated
1RMs (computed server-side) and the athlete's injury notes verbatim.
"""

from app.models import UserProfile

SYSTEM_PROMPT = (
    "You are the AI strength coach inside Quwwa, a workout tracking app. "
    "You produce structured coaching output as JSON matching the requested schema exactly. "
    "Be specific: reference the athlete's actual numbers, never invent history, "
    "and always respect their injury notes when prescribing exercises."
)


def _fmt_weight(value: float | None) -> str:
    if value is None:
        return "?"
    return f"{value:g}"


def _profile_block(profile: UserProfile) -> str:
    equipment = ", ".join(profile.equipment) if profile.equipment else "unknown"
    return (
        f"Athlete profile:\n"
        f"- Goal: {profile.training_goal}\n"
        f"- Experience: {profile.experience}\n"
        f"- Training days per week: {profile.training_days}\n"
        f"- Available equipment: {equipment}\n"
        f"- Injury notes: {profile.injury_notes or 'None'}"
    )


def _sets_lines(sets: list[dict]) -> list[str]:
    lines = []
    for s in sets:
        line = f"  - {s['exercise_name']}: {_fmt_weight(s['weight_kg'])}kg × {s['reps'] if s['reps'] is not None else '?'} reps"
        if s["rpe"] is not None:
            line += f" @ RPE {s['rpe']}"
        if s["is_warmup"]:
            line += " (warmup)"
        lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# 1. Next session planner


def build_next_session_prompt(
    profile: UserProfile,
    target_muscles: list[str],
    recent_sessions: list[dict],
    e1rms: list[dict],
) -> str:
    parts = [
        "You are a strength coach. Your athlete is logging their workouts and you are "
        "prescribing their next session.",
        "",
        _profile_block(profile),
        "",
    ]
    if recent_sessions:
        parts.append(
            f"Here are their last {len(recent_sessions)} sessions involving the muscle "
            f"groups they'll train today ({', '.join(target_muscles)}):"
        )
        for sp in recent_sessions:
            rpe = sp["session_rpe"] if sp["session_rpe"] is not None else "not rated"
            parts.append("")
            parts.append(f"Session on {sp['date']} (session RPE: {rpe}):")
            parts.extend(_sets_lines(sp["sets"]))
    else:
        parts.append(
            f"They have no logged sessions yet for today's target muscle groups "
            f"({', '.join(target_muscles)}). Prescribe a sensible first session based on "
            f"their profile, with conservative starting weights they can comfortably "
            f"adjust upward."
        )
    if e1rms:
        parts.append("")
        parts.append("Their 1-rep max estimates (calculated from logged data):")
        parts.extend(f"- {e['exercise_name']}: ~{e['e1rm_kg']}kg" for e in e1rms)
    parts.extend(
        [
            "",
            "Based on this history, generate their next session plan. Apply progressive "
            "overload where appropriate — increase weight if their last set RPE was ≤7, "
            "keep weight if RPE was 8, reduce volume if RPE was 9–10 consistently. "
            "Only prescribe exercises that fit their available equipment, and never "
            "prescribe anything that conflicts with their injury notes.",
        ]
    )
    return "\n".join(parts)


NEXT_SESSION_SCHEMA = {
    "type": "object",
    "properties": {
        "session_focus": {
            "type": "string",
            "description": "e.g. 'Upper — chest and triceps emphasis'",
        },
        "coaching_note": {
            "type": "string",
            "description": "2–3 sentences explaining your reasoning",
        },
        "exercises": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "exercise_name": {"type": "string"},
                    "sets": {"type": "integer"},
                    "target_reps": {"type": "string", "description": "e.g. '4–6' or '8–10'"},
                    "target_weight_kg": {"type": "number"},
                    "progression_reason": {
                        "type": "string",
                        "description": "why this weight vs last time",
                    },
                    "rpe_target": {"type": "number", "description": "6–9"},
                },
                "required": [
                    "exercise_name",
                    "sets",
                    "target_reps",
                    "target_weight_kg",
                    "progression_reason",
                    "rpe_target",
                ],
                "additionalProperties": False,
            },
        },
        "deload_recommended": {"type": "boolean"},
        "deload_reason": {"type": ["string", "null"]},
    },
    "required": [
        "session_focus",
        "coaching_note",
        "exercises",
        "deload_recommended",
        "deload_reason",
    ],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# 2. Plateau detector


def build_plateau_prompt(
    profile: UserProfile,
    exercise_name: str,
    sessions: list[dict],
) -> str:
    """sessions: oldest → newest, each {date, best set line info, best_e1rm}."""
    lines = [
        "You are analyzing strength progression data for a single exercise.",
        "",
        f"Exercise: {exercise_name}",
        f"Athlete goal: {profile.training_goal}",
        f"Injury notes: {profile.injury_notes or 'None'}",
        f"Last {len(sessions)} sessions of working sets (excluding warmups):",
        "",
    ]
    for sp in sessions:
        set_strs = [
            f"{_fmt_weight(s['weight_kg'])}kg × {s['reps']} reps (RPE {s['rpe'] if s['rpe'] is not None else '?'})"
            for s in sp["sets"]
            if not s["is_warmup"]
        ]
        lines.append(f"{sp['date']}: " + "; ".join(set_strs))
    e1rms = [str(sp["best_e1rm"]) for sp in sessions if sp["best_e1rm"]]
    lines.extend(
        [
            "",
            f"Estimated 1RM trend: {' → '.join(e1rms)} (oldest → newest)",
            "",
            "Analyze whether this athlete is:",
            "1. Progressing normally",
            "2. Plateaued (no meaningful e1RM increase over last 4+ sessions)",
            "3. Regressing (e1RM declining)",
            "4. Possibly fatigued (RPE increasing while weight stays the same)",
        ]
    )
    return "\n".join(lines)


PLATEAU_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["progressing", "plateaued", "regressing", "fatigued"],
        },
        "trend_summary": {
            "type": "string",
            "description": "one sentence, specific numbers",
        },
        "recommendation": {
            "type": "string",
            "description": "concrete action, e.g. 'Try a 5x5 protocol at 90% of current working weight for 2 weeks'",
        },
        "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["status", "trend_summary", "recommendation", "urgency"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# 3. Weekly review


def build_weekly_review_prompt(profile: UserProfile, data: dict) -> str:
    lines = [
        "You are writing a weekly training review for an athlete.",
        "",
        f"Athlete goal: {profile.training_goal} ({profile.experience}). "
        f"Injury notes: {profile.injury_notes or 'None'}",
        "",
        f"Week of {data['week_start']:%Y-%m-%d} to {data['week_end']:%Y-%m-%d}:",
        f"- Sessions completed: {data['session_count']} / {profile.training_days} planned",
        f"- Total working sets logged: {data['total_sets']}",
        f"- Average session RPE: {data['avg_rpe'] if data['avg_rpe'] is not None else 'not rated'}",
        "",
        "Volume breakdown by muscle group (working sets only):",
    ]
    for mv in data["muscle_volumes"]:
        lines.append(
            f"- {mv['muscle']}: {mv['sets']} sets "
            f"(recommended weekly range: {mv['min_sets']}–{mv['max_sets']})"
        )
    lines.append("")
    if data["prs"]:
        lines.append("Personal records set this week:")
        for pr in data["prs"]:
            lines.append(
                f"- {pr['exercise_name']}: {_fmt_weight(pr['weight_kg'])}kg × {pr['reps']} "
                f"(previous best: {pr['previous_best']})"
            )
    else:
        lines.append("Personal records set this week: none")
    lines.extend(
        [
            "",
            "Write a brief, direct weekly review. Be specific — reference actual numbers. "
            "Don't be a cheerleader; be a coach. If something was underdone or overdone, "
            "say so. In volume_status, include one entry per muscle group that was "
            "meaningfully trained or notably neglected this week.",
        ]
    )
    return "\n".join(lines)


WEEKLY_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {
            "type": "string",
            "description": "one punchy sentence summarizing the week",
        },
        "positives": {"type": "array", "items": {"type": "string"}},
        "concerns": {"type": "array", "items": {"type": "string"}},
        "focus_next_week": {"type": "string", "description": "one concrete priority"},
        "volume_status": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "muscle_group": {"type": "string"},
                    "status": {"type": "string", "enum": ["under", "optimal", "over"]},
                },
                "required": ["muscle_group", "status"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["headline", "positives", "concerns", "focus_next_week", "volume_status"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# 4. Deload advisor


def build_deload_prompt(profile: UserProfile, data: dict) -> str:
    lines = [
        "You are assessing whether an athlete needs a deload week.",
        "",
        f"Athlete goal: {profile.training_goal} ({profile.experience}), "
        f"{profile.training_days} planned sessions/week. "
        f"Injury notes: {profile.injury_notes or 'None'}",
        "",
        "Last 3 weeks of training data (oldest first):",
        "",
    ]
    for w in data["weeks"]:
        lines.extend(
            [
                f"Week {w['week_number']} (starting {w['start']:%Y-%m-%d}):",
                f"  - Sessions: {w['session_count']}",
                f"  - Average session RPE: {w['avg_rpe'] if w['avg_rpe'] is not None else 'not rated'}",
                f"  - Total working sets: {w['total_sets']}",
                f"  - Sessions with RPE ≥ 9: {w['high_rpe_count']}",
            ]
        )
    lines.extend(
        [
            "",
            f"Trend: {data['rpe_trend']} (improving / stable / worsening)",
            f"Bodyweight trend (if logged): {data['bw_trend']}",
            "",
            "Signs of accumulated fatigue to check:",
            "- RPE increasing week-over-week despite no weight increase",
            "- Session count dropping (missed sessions = fatigue signal)",
            "- Bodyweight dropping unexpectedly",
            "",
            "Advise whether a deload is needed, and if so, what kind.",
        ]
    )
    return "\n".join(lines)


DELOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "deload_needed": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "rationale": {
            "type": "string",
            "description": "specific, reference the numbers",
        },
        "deload_type": {
            "type": ["string", "null"],
            "enum": ["full", "volume", "intensity", None],
        },
        "deload_protocol": {
            "type": ["string", "null"],
            "description": "e.g. '50% of normal volume, keep weights the same, for 5–7 days'",
        },
    },
    "required": ["deload_needed", "confidence", "rationale", "deload_type", "deload_protocol"],
    "additionalProperties": False,
}
