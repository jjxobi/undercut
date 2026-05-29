import pandas as pd
import pytest

from modeling.evaluation import position_gap


def _results() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Season": 2023, "Round": 1, "Code": "VER", "Status": "Finished"},
            {"Season": 2023, "Round": 1, "Code": "HAM", "Status": "Finished"},
            {"Season": 2023, "Round": 1, "Code": "PER", "Status": "Finished"},
            {"Season": 2023, "Round": 1, "Code": "ALO", "Status": "+1 Lap"},
        ]
    )


def test_estimate_seconds_per_position_uses_only_same_lap_adjacent_pairs():
    # VER (P1) and HAM (P2) both complete 30 laps, 10s apart -- a valid pair,
    # played out across enough rounds to clear MIN_OBSERVATIONS. PER (P3) is a
    # lap down at 29 laps each round -- its gap to HAM is not comparable and
    # must be excluded, even though it's the next position down.
    rounds = range(1, position_gap.MIN_OBSERVATIONS + 1)
    laps = pd.DataFrame(
        [
            row
            for round_number in rounds
            for row in (
                {"Season": 2023, "Round": round_number, "Driver": "VER", "LapNumber": 30, "Time": pd.Timedelta(seconds=5000), "Position": 1.0},
                {"Season": 2023, "Round": round_number, "Driver": "HAM", "LapNumber": 30, "Time": pd.Timedelta(seconds=5010), "Position": 2.0},
                {"Season": 2023, "Round": round_number, "Driver": "PER", "LapNumber": 29, "Time": pd.Timedelta(seconds=4995), "Position": 3.0},
            )
        ]
    )
    results = pd.DataFrame(
        [
            {"Season": 2023, "Round": round_number, "Code": code, "Status": "Finished"}
            for round_number in rounds
            for code in ("VER", "HAM", "PER")
        ]
    )

    gap = position_gap.estimate_seconds_per_position(laps, results)

    assert gap == pytest.approx(10.0)


def test_estimate_seconds_per_position_excludes_non_finishers():
    # VER and HAM finish together on the lead lap every round, 10s apart.
    # PER shows up in the lap data too but never has a matching results row,
    # so it has to be dropped entirely rather than folded into the gaps as
    # a third classified finisher.
    rounds = range(1, position_gap.MIN_OBSERVATIONS + 1)
    laps = pd.DataFrame(
        [
            row
            for round_number in rounds
            for row in (
                {"Season": 2023, "Round": round_number, "Driver": "VER", "LapNumber": 30, "Time": pd.Timedelta(seconds=5000), "Position": 1.0},
                {"Season": 2023, "Round": round_number, "Driver": "HAM", "LapNumber": 30, "Time": pd.Timedelta(seconds=5010), "Position": 2.0},
                {"Season": 2023, "Round": round_number, "Driver": "PER", "LapNumber": 30, "Time": pd.Timedelta(seconds=5100), "Position": 3.0},
            )
        ]
    )
    results = pd.DataFrame(
        [
            {"Season": 2023, "Round": round_number, "Code": code, "Status": "Finished"}
            for round_number in rounds
            for code in ("VER", "HAM")
        ]
    )

    gap = position_gap.estimate_seconds_per_position(laps, results)

    assert gap == pytest.approx(10.0)


def test_estimate_seconds_per_position_raises_below_minimum_observations():
    laps = pd.DataFrame(
        [
            {"Season": 2023, "Round": 1, "Driver": "VER", "LapNumber": 30, "Time": pd.Timedelta(seconds=5000), "Position": 1.0},
            {"Season": 2023, "Round": 1, "Driver": "HAM", "LapNumber": 30, "Time": pd.Timedelta(seconds=5010), "Position": 2.0},
        ]
    )

    with pytest.raises(ValueError):
        position_gap.estimate_seconds_per_position(laps, _results())
