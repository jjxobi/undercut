import numpy as np
import pandas as pd

from modeling.degradation import filters


def test_accurate_laps_keeps_only_accurate_timed_laps_with_valid_tyre_life():
    laps = pd.DataFrame(
        {
            "IsAccurate": [True, False, True, True, True],
            "LapTime": [
                pd.Timedelta(seconds=90),
                pd.Timedelta(seconds=95),
                pd.NaT,
                pd.Timedelta(seconds=88),
                pd.Timedelta(seconds=91),
            ],
            "TyreLife": [3, 1, 5, np.nan, 0],
        }
    )

    result = filters.accurate_laps(laps)

    assert len(result) == 1
    assert result.iloc[0]["TyreLife"] == 3


def test_accurate_laps_resets_index():
    laps = pd.DataFrame(
        {
            "IsAccurate": [False, True],
            "LapTime": [pd.Timedelta(seconds=90), pd.Timedelta(seconds=91)],
            "TyreLife": [1, 2],
        }
    )

    result = filters.accurate_laps(laps)

    assert list(result.index) == [0]


def test_exclude_rain_affected_dry_compound_laps_drops_dry_compound_in_rain():
    frame = pd.DataFrame(
        {
            "Compound": ["MEDIUM", "MEDIUM", "WET", "HARD"],
            "Rainfall": [True, False, True, False],
        }
    )

    result = filters.exclude_rain_affected_dry_compound_laps(frame)

    assert len(result) == 3
    assert list(result["Compound"]) == ["MEDIUM", "WET", "HARD"]


def test_exclude_rain_affected_dry_compound_laps_keeps_wet_compound_in_rain():
    frame = pd.DataFrame({"Compound": ["INTERMEDIATE", "WET"], "Rainfall": [True, True]})

    result = filters.exclude_rain_affected_dry_compound_laps(frame)

    assert len(result) == 2
