from types import SimpleNamespace

import pandas as pd

from scripts import build_dataset

SCHEDULE = [
    {"round": "1", "raceName": "Bahrain Grand Prix", "date": "2023-03-05",
     "Circuit": {"circuitId": "bahrain"}}
]

RESULTS = [
    {"position": "1", "grid": "2", "status": "Finished",
     "Driver": {"driverId": "max_verstappen"}}
]


def _patch_pipeline(monkeypatch):
    monkeypatch.setattr(build_dataset.fastf1_source, "enable_cache", lambda: None)
    monkeypatch.setattr(
        build_dataset.jolpica_source, "season_schedule", lambda season, refresh=False: SCHEDULE
    )
    monkeypatch.setattr(
        build_dataset.jolpica_source, "race_results", lambda season, rnd, refresh=False: RESULTS
    )
    fake_session = SimpleNamespace()
    monkeypatch.setattr(
        build_dataset.fastf1_source, "load_race_session", lambda season, rnd: fake_session
    )
    laps = pd.DataFrame({"Season": [2023], "Round": [1], "Driver": ["VER"], "Stint": [1],
                          "Compound": ["MEDIUM"], "LapNumber": [1],
                          "PitInTime": [pd.NaT], "PitOutTime": [pd.NaT]})
    monkeypatch.setattr(
        build_dataset.fastf1_source, "laps_frame", lambda session, season, rnd: laps
    )
    monkeypatch.setattr(
        build_dataset.fastf1_source, "track_status_frame",
        lambda session, season, rnd: pd.DataFrame({"Season": [2023], "Round": [1],
                                                     "Time": [pd.Timedelta(0)], "Status": ["1"]}),
    )
    monkeypatch.setattr(
        build_dataset.fastf1_source, "weather_frame",
        lambda session, season, rnd: pd.DataFrame({"Season": [2023], "Round": [1],
                                                     "AirTemp": [22.0]}),
    )
    monkeypatch.setattr(
        build_dataset.fastf1_source, "stints_frame",
        lambda laps_df: pd.DataFrame({"Season": [2023], "Round": [1], "Driver": ["VER"],
                                       "Stint": [1], "Compound": ["MEDIUM"], "StartLap": [1],
                                       "EndLap": [1], "StintLength": [1]}),
    )
    monkeypatch.setattr(
        build_dataset.fastf1_source, "pit_stops_frame", lambda laps_df: pd.DataFrame()
    )


def test_build_returns_all_expected_tables(monkeypatch):
    _patch_pipeline(monkeypatch)

    tables = build_dataset.build([2023])

    assert set(tables) == {
        "laps", "track_status", "weather", "stints", "pit_stops", "schedule", "results"
    }
    assert len(tables["schedule"]) == 1
    assert tables["schedule"].iloc[0]["CircuitId"] == "bahrain"
    assert tables["results"].iloc[0]["Driver"] == "max_verstappen"
    assert tables["results"].iloc[0]["Position"] == 1


TWO_ROUND_SCHEDULE = [
    {"round": "1", "raceName": "Bahrain Grand Prix", "date": "2023-03-05",
     "Circuit": {"circuitId": "bahrain"}},
    {"round": "2", "raceName": "Saudi Arabian Grand Prix", "date": "2023-03-19",
     "Circuit": {"circuitId": "jeddah"}},
]


def test_build_skips_failed_session_but_keeps_schedule_and_results(monkeypatch, capsys):
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(
        build_dataset.jolpica_source, "season_schedule",
        lambda season, refresh=False: TWO_ROUND_SCHEDULE,
    )

    def failing_load_race_session(season, round_number):
        if round_number == 2:
            raise RuntimeError("session data unavailable")
        return SimpleNamespace()

    monkeypatch.setattr(
        build_dataset.fastf1_source, "load_race_session", failing_load_race_session
    )

    tables = build_dataset.build([2023])

    assert set(tables["schedule"]["Round"]) == {1, 2}
    assert set(tables["results"]["Round"]) == {1, 2}
    for name in ("laps", "track_status", "weather", "stints", "pit_stops"):
        assert 2 not in set(tables[name].get("Round", []))

    captured = capsys.readouterr()
    assert "skip 2023 round 2" in captured.out


def test_build_skips_race_when_laps_frame_fails_after_session_loads(monkeypatch, capsys):
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(
        build_dataset.jolpica_source, "season_schedule",
        lambda season, refresh=False: TWO_ROUND_SCHEDULE,
    )

    # load_race_session succeeds for every race and never raises - this
    # reproduces FastF1 sessions that load "successfully" but leave internal
    # data unset, so the real failure only surfaces later when a downstream
    # frame accessor touches the session.
    monkeypatch.setattr(
        build_dataset.fastf1_source, "load_race_session",
        lambda season, round_number: SimpleNamespace(),
    )

    def failing_laps_frame(session, season, round_number):
        if round_number == 2:
            raise RuntimeError("The data you are trying to access has not been loaded yet")
        return pd.DataFrame({"Season": [2023], "Round": [1], "Driver": ["VER"], "Stint": [1],
                              "Compound": ["MEDIUM"], "LapNumber": [1],
                              "PitInTime": [pd.NaT], "PitOutTime": [pd.NaT]})

    monkeypatch.setattr(build_dataset.fastf1_source, "laps_frame", failing_laps_frame)

    tables = build_dataset.build([2023])

    assert set(tables["schedule"]["Round"]) == {1, 2}
    assert set(tables["results"]["Round"]) == {1, 2}
    for name in ("laps", "track_status", "weather", "stints", "pit_stops"):
        assert 2 not in set(tables[name].get("Round", []))
    # laps for the untouched round 1 race must still be present - the fix
    # isolates the failure per-race rather than aborting the whole run.
    assert set(tables["laps"]["Round"]) == {1}

    captured = capsys.readouterr()
    assert "skip 2023 round 2" in captured.out


def test_write_tables_writes_parquet_files(tmp_path, monkeypatch):
    _patch_pipeline(monkeypatch)
    tables = build_dataset.build([2023])

    build_dataset.write_tables(tables, tmp_path)

    assert (tmp_path / "laps.parquet").exists()
    assert (tmp_path / "schedule.parquet").exists()
    round_trip = pd.read_parquet(tmp_path / "results.parquet")
    assert round_trip.iloc[0]["Driver"] == "max_verstappen"
