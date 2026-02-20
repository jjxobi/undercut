from types import SimpleNamespace

import pandas as pd

from modeling.ingest import fastf1_source


class _FakeSession:
    def __init__(self, laps, track_status, weather_data):
        self.laps = laps
        self.track_status = track_status
        self.weather_data = weather_data
        self.load_calls: list[dict] = []

    def load(self, **kwargs):
        self.load_calls.append(kwargs)


def test_enable_cache_creates_dir_and_calls_fastf1(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        fastf1_source.fastf1.Cache, "enable_cache", lambda path: calls.append(path)
    )
    cache_dir = tmp_path / "fastf1_cache"

    fastf1_source.enable_cache(cache_dir)

    assert cache_dir.exists()
    assert calls == [str(cache_dir)]


def test_load_race_session_calls_get_session_and_load(monkeypatch):
    fake_session = _FakeSession(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    calls = []

    def fake_get_session(season, round_number, identifier):
        calls.append((season, round_number, identifier))
        return fake_session

    monkeypatch.setattr(fastf1_source.fastf1, "get_session", fake_get_session)

    result = fastf1_source.load_race_session(2023, 5)

    assert result is fake_session
    assert calls == [(2023, 5, "R")]
    assert fake_session.load_calls == [
        {"laps": True, "weather": True, "telemetry": False, "messages": False}
    ]


def test_laps_frame_adds_season_and_round():
    laps = pd.DataFrame({"Driver": ["VER"], "LapNumber": [1]})
    session = SimpleNamespace(laps=laps)

    result = fastf1_source.laps_frame(session, 2023, 5)

    assert list(result.columns[:2]) == ["Season", "Round"]
    assert result.iloc[0]["Season"] == 2023
    assert result.iloc[0]["Round"] == 5


def test_track_status_frame_adds_season_and_round():
    status = pd.DataFrame({"Time": [pd.Timedelta(seconds=0)], "Status": ["1"]})
    session = SimpleNamespace(track_status=status)

    result = fastf1_source.track_status_frame(session, 2023, 5)

    assert result.iloc[0]["Season"] == 2023
    assert result.iloc[0]["Round"] == 5
    assert result.iloc[0]["Status"] == "1"


def test_weather_frame_adds_season_and_round():
    weather = pd.DataFrame({"Time": [pd.Timedelta(seconds=0)], "AirTemp": [22.0]})
    session = SimpleNamespace(weather_data=weather)

    result = fastf1_source.weather_frame(session, 2023, 5)

    assert result.iloc[0]["Season"] == 2023
    assert result.iloc[0]["Round"] == 5


def test_stints_frame_groups_by_driver_and_stint():
    laps = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023, 2023],
            "Round": [5, 5, 5, 5],
            "Driver": ["VER", "VER", "VER", "VER"],
            "Stint": [1, 1, 2, 2],
            "Compound": ["MEDIUM", "MEDIUM", "HARD", "HARD"],
            "LapNumber": [1, 2, 3, 4],
        }
    )

    result = fastf1_source.stints_frame(laps)

    assert len(result) == 2
    first = result[result["Stint"] == 1].iloc[0]
    assert first["Compound"] == "MEDIUM"
    assert first["StartLap"] == 1
    assert first["EndLap"] == 2
    assert first["StintLength"] == 2


def test_pit_stops_frame_keeps_only_rows_with_pit_in_time():
    laps = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [5, 5],
            "Driver": ["VER", "VER"],
            "LapNumber": [10, 11],
            "Stint": [1, 2],
            "PitInTime": [pd.Timedelta(seconds=100), pd.NaT],
            "PitOutTime": [pd.Timedelta(seconds=120), pd.NaT],
        }
    )

    result = fastf1_source.pit_stops_frame(laps)

    assert len(result) == 1
    assert result.iloc[0]["LapNumber"] == 10
