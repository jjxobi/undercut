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
            "TrackStatus": ["1", "1", "1", "1", "1"],
            "Time": [
                pd.Timedelta(minutes=1),
                pd.Timedelta(minutes=2),
                pd.Timedelta(minutes=3),
                pd.Timedelta(minutes=4),
                pd.Timedelta(minutes=5),
            ],
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
            "TrackStatus": ["1", "1"],
            "Time": [pd.Timedelta(minutes=1), pd.Timedelta(minutes=2)],
        }
    )

    result = filters.accurate_laps(laps)

    assert list(result.index) == [0]


def test_accurate_laps_excludes_yellow_flag_laps():
    laps = pd.DataFrame(
        {
            "IsAccurate": [True, True],
            "LapTime": [pd.Timedelta(seconds=90), pd.Timedelta(seconds=91)],
            "TyreLife": [3, 4],
            "TrackStatus": ["1", "2"],
            "Time": [pd.Timedelta(minutes=1), pd.Timedelta(minutes=2)],
        }
    )

    result = filters.accurate_laps(laps)

    assert len(result) == 1
    assert result.iloc[0]["TyreLife"] == 3


def test_accurate_laps_excludes_laps_with_null_time():
    laps = pd.DataFrame(
        {
            "IsAccurate": [True, True],
            "LapTime": [pd.Timedelta(seconds=90), pd.Timedelta(seconds=91)],
            "TyreLife": [3, 4],
            "TrackStatus": ["1", "1"],
            "Time": [pd.Timedelta(minutes=1), pd.NaT],
        }
    )

    result = filters.accurate_laps(laps)

    assert len(result) == 1
    assert result.iloc[0]["TyreLife"] == 3


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


def test_exclude_rain_affected_dry_compound_laps_recognizes_era_specific_slick_names():
    # WET_COMPOUNDS is an exclusion set, not an allowlist, so a slick compound
    # name that predates the current SOFT/MEDIUM/HARD naming (e.g. 2018's
    # HYPERSOFT) must still be recognized as dry and dropped when rainy.
    frame = pd.DataFrame({"Compound": ["HYPERSOFT", "ULTRASOFT", "SUPERSOFT"], "Rainfall": [True, True, True]})

    result = filters.exclude_rain_affected_dry_compound_laps(frame)

    assert len(result) == 0


def test_exclude_rain_affected_dry_compound_laps_treats_missing_rainfall_as_dry():
    frame = pd.DataFrame({"Compound": ["MEDIUM"], "Rainfall": [np.nan]})

    result = filters.exclude_rain_affected_dry_compound_laps(frame)

    assert len(result) == 1
