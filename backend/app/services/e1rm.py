"""Estimated 1RM via the Epley formula. Computed server-side before prompting
so the AI reasons over a normalized strength baseline instead of raw set data."""


def epley_1rm(weight_kg: float, reps: int) -> float:
    if reps <= 0 or weight_kg <= 0:
        return 0.0
    return round(weight_kg * (1 + reps / 30), 1)


def best_e1rm(sets: list[dict]) -> float | None:
    """Best estimated 1RM across working (non-warmup) sets.

    Each set dict needs weight_kg, reps, is_warmup keys.
    """
    values = [
        epley_1rm(float(s["weight_kg"]), int(s["reps"]))
        for s in sets
        if not s.get("is_warmup") and s.get("weight_kg") and s.get("reps")
    ]
    values = [v for v in values if v > 0]
    return max(values) if values else None
