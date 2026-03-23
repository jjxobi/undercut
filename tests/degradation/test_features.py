import pandas as pd

from modeling import config
from modeling.degradation import features


def _laps():
    return pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "Driver": ["VER", "VER"],
            "LapNumber": [5, 6],
            "TyreLife": [5, 6],
            "Time": [pd.Timedelta(minutes=10), pd.Timedelta(minutes=12)],
            "LapTime": [pd.Timedelta(seconds=91.5), pd.Timedelta(seconds=91.8)],
        }
    )


def _schedule():
    return pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]})


def _weather():
    return pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "Time": [pd.Timedelta(minutes=9), pd.Timedelta(minutes=11)],
            "TrackTemp": [35.0, 36.0],
            "AirTemp": [25.0, 25.5],
            "Rainfall": [False, False],
        }
    )


def test_add_circuit_joins_circuit_id_by_season_and_round():
    result = features.add_circuit(_laps(), _schedule())

    assert (result["CircuitId"] == "bahrain").all()


def test_add_weather_attaches_nearest_reading_within_race():
    result = features.add_weather(_laps(), _weather())

    assert result.iloc[0]["TrackTemp"] == 35.0
    assert result.iloc[1]["TrackTemp"] == 36.0


def test_add_weather_handles_race_with_no_weather_rows():
    laps = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [2, 2],
            "Driver": ["VER", "VER"],
            "LapNumber": [1, 2],
            "TyreLife": [1, 2],
            "Time": [pd.Timedelta(minutes=1), pd.Timedelta(minutes=2)],
            "LapTime": [pd.Timedelta(seconds=90.0), pd.Timedelta(seconds=90.5)],
        }
    )
    # weather fixture only has rows for Round 1 -- Round 2 has zero matching weather rows
    weather = _weather()

    result = features.add_weather(laps, weather)

    assert len(result) == 2
    assert result["TrackTemp"].isna().all()
    assert result["AirTemp"].isna().all()
    assert result["Rainfall"].isna().all()


def test_build_training_frame_computes_engineered_columns():
    result = features.build_training_frame(_laps(), _schedule(), _weather())

    assert result.iloc[0]["CircuitId"] == "bahrain"
    assert result.iloc[0]["TrackTemp"] == 35.0
    assert result.iloc[0]["LapTimeSeconds"] == 91.5
    assert result.iloc[0]["TyreLifeSquared"] == 25
    assert result.iloc[0]["RaceLapNumber"] == 5
    assert result.iloc[1]["LapTimeSeconds"] == 91.8
    assert result.iloc[1]["TyreLifeSquared"] == 36

    assert result.iloc[0]["CorrectedLapTimeSeconds"] == 91.5 + 0.07 * 5
    assert result.iloc[1]["CorrectedLapTimeSeconds"] == 91.8 + 0.07 * 6
    assert result.iloc[0]["RegulationEra"] == config.regulation_era(2023)
    assert result.iloc[0]["RegulationEra"] == "2022-2025 ground-effect"


def test_add_stint_key_builds_composite_identifier_for_one_continuous_run():
    frame = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023],
            "Round": [1, 1, 5],
            "Driver": ["VER", "VER", "HAM"],
            "Stint": [1, 2, 1],
        }
    )

    result = features.add_stint_key(frame)

    assert list(result["StintKey"]) == ["2023_1_VER_1", "2023_1_VER_2", "2023_5_HAM_1"]


def test_add_variant_maps_by_season_round_circuit_key():
    frame = pd.DataFrame(
        {
            "Season": [2020, 2020, 2021],
            "Round": [1, 16, 3],
            "CircuitId": ["bahrain", "bahrain", "bahrain"],
        }
    )
    variant_map = pd.Series(
        {
            (2020, 1, "bahrain"): "bahrain_v0",
            (2020, 16, "bahrain"): "bahrain_v1",
            (2021, 3, "bahrain"): "bahrain_v0",
        }
    )

    result = features.add_variant(frame, variant_map)

    assert list(result["Variant"]) == ["bahrain_v0", "bahrain_v1", "bahrain_v0"]


def test_add_variant_leaves_unmapped_race_as_nan():
    frame = pd.DataFrame({"Season": [2022], "Round": [99], "CircuitId": ["imola"]})
    variant_map = pd.Series({(2020, 1, "bahrain"): "bahrain_v0"})

    result = features.add_variant(frame, variant_map)

    assert result["Variant"].isna().all()
