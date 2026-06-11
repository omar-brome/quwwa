from app.services.e1rm import best_e1rm, epley_1rm


def test_epley_formula():
    assert epley_1rm(100, 8) == 126.7  # 100 * (1 + 8/30)
    assert epley_1rm(100, 1) == 103.3
    assert epley_1rm(0, 8) == 0.0
    assert epley_1rm(100, 0) == 0.0


def test_best_e1rm_excludes_warmups():
    sets = [
        {"weight_kg": 60, "reps": 10, "is_warmup": True},
        {"weight_kg": 100, "reps": 5, "is_warmup": False},
        {"weight_kg": 90, "reps": 8, "is_warmup": False},
    ]
    # 100x5 -> 116.7, 90x8 -> 114.0; warmup 60x10 (=80) ignored
    assert best_e1rm(sets) == 116.7


def test_best_e1rm_empty():
    assert best_e1rm([]) is None
    assert best_e1rm([{"weight_kg": None, "reps": 5, "is_warmup": False}]) is None
