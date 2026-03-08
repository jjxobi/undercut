import pandas as pd

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


def test_build_training_frame_computes_engineered_columns():
    result = features.build_training_frame(_laps(), _schedule(), _weather())

    assert result.iloc[0]["CircuitId"] == "bahrain"
    assert result.iloc[0]["TrackTemp"] == 35.0
    assert result.iloc[0]["LapTimeSeconds"] == 91.5
    assert result.iloc[0]["TyreLifeSquared"] == 25
    assert result.iloc[0]["RaceLapNumber"] == 5
    assert result.iloc[1]["LapTimeSeconds"] == 91.8
    assert result.iloc[1]["TyreLifeSquared"] == 36
