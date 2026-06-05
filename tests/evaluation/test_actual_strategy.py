import pandas as pd

from modeling.evaluation import actual_strategy
from modeling.optimization import solver


def _stints() -> pd.DataFrame:
    return pd.DataFrame(
        [
            # VER: matches a candidate sequence, full race distance, finished -- keep
            {"Season": 2023, "Round": 1, "Driver": "VER", "Stint": 1.0, "Compound": "SOFT", "StintLength": 15.0},
            {"Season": 2023, "Round": 1, "Driver": "VER", "Stint": 2.0, "Compound": "MEDIUM", "StintLength": 15.0},
            # PER: matches a candidate sequence but is a lap down (only 25 of 30 laps) -- drop
            {"Season": 2023, "Round": 1, "Driver": "PER", "Stint": 1.0, "Compound": "SOFT", "StintLength": 15.0},
            {"Season": 2023, "Round": 1, "Driver": "PER", "Stint": 2.0, "Compound": "MEDIUM", "StintLength": 10.0},
            # HAM: full distance and finished, but SOFT-SOFT isn't a candidate sequence -- drop
            {"Season": 2023, "Round": 1, "Driver": "HAM", "Stint": 1.0, "Compound": "SOFT", "StintLength": 15.0},
            {"Season": 2023, "Round": 1, "Driver": "HAM", "Stint": 2.0, "Compound": "SOFT", "StintLength": 15.0},
            # ALO: matches a candidate sequence and full distance, but did not finish -- drop
            {"Season": 2023, "Round": 1, "Driver": "ALO", "Stint": 1.0, "Compound": "SOFT", "StintLength": 15.0},
            {"Season": 2023, "Round": 1, "Driver": "ALO", "Stint": 2.0, "Compound": "MEDIUM", "StintLength": 15.0},
        ]
    )


def _results() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Season": 2023, "Round": 1, "Code": "VER", "Status": "Finished"},
            {"Season": 2023, "Round": 1, "Code": "PER", "Status": "+1 Lap"},
            {"Season": 2023, "Round": 1, "Code": "HAM", "Status": "Finished"},
            {"Season": 2023, "Round": 1, "Code": "ALO", "Status": "Retired"},
        ]
    )


def _race_lengths() -> pd.Series:
    laps = pd.DataFrame({"Season": [2023] * 3, "Round": [1] * 3, "LapNumber": [28, 29, 30]})
    return laps.groupby(["Season", "Round"])["LapNumber"].max()


def test_extract_actual_strategies_keeps_only_full_distance_finishers_on_a_candidate_sequence():
    result = actual_strategy.extract_actual_strategies(_stints(), _results(), _race_lengths())

    assert result["driver"].tolist() == ["VER"]
    assert result.iloc[0]["season"] == 2023
    assert result.iloc[0]["round"] == 1
    assert result.iloc[0]["compounds"] == ["SOFT", "MEDIUM"]
    assert result.iloc[0]["stint_lengths"] == [15, 15]


def _stints_with_short_stint() -> pd.DataFrame:
    # SAI: matches a candidate sequence and full race distance, but the first
    # stint is a single lap -- shorter than the solver would ever search over -- drop
    return pd.concat(
        [
            _stints(),
            pd.DataFrame(
                [
                    {
                        "Season": 2023,
                        "Round": 1,
                        "Driver": "SAI",
                        "Stint": 1.0,
                        "Compound": "SOFT",
                        "StintLength": 1.0,
                    },
                    {
                        "Season": 2023,
                        "Round": 1,
                        "Driver": "SAI",
                        "Stint": 2.0,
                        "Compound": "HARD",
                        "StintLength": 29.0,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )


def _results_with_short_stint() -> pd.DataFrame:
    return pd.concat(
        [_results(), pd.DataFrame([{"Season": 2023, "Round": 1, "Code": "SAI", "Status": "Finished"}])],
        ignore_index=True,
    )


def test_extract_actual_strategies_drops_stints_shorter_than_the_solvers_minimum():
    assert min([1, 29]) < solver.MIN_STINT_LENGTH

    result = actual_strategy.extract_actual_strategies(
        _stints_with_short_stint(), _results_with_short_stint(), _race_lengths()
    )

    assert "SAI" not in result["driver"].tolist()
    assert result["driver"].tolist() == ["VER"]


def test_extract_actual_strategies_returns_empty_frame_with_expected_columns_when_nothing_matches():
    empty_stints = pd.DataFrame(columns=["Season", "Round", "Driver", "Stint", "Compound", "StintLength"])

    result = actual_strategy.extract_actual_strategies(empty_stints, _results(), _race_lengths())

    assert list(result.columns) == actual_strategy.RESULT_COLUMNS
    assert len(result) == 0
