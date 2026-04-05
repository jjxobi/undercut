import pandas as pd

from modeling.hazard import features


def test_build_hazard_panel_produces_one_row_per_race_lap():
    laps = pd.DataFrame(
        {
            "Season": [2023] * 3,
            "Round": [1] * 3,
            "LapNumber": [1, 2, 3],
            "LapStartTime": [
                pd.Timedelta(seconds=0),
                pd.Timedelta(seconds=90),
                pd.Timedelta(seconds=180),
            ],
        }
    )
    track_status = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "Time": [pd.Timedelta(seconds=0), pd.Timedelta(seconds=185)],
            "Status": ["1", "4"],
        }
    )
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["monza"]})

    panel = features.build_hazard_panel(laps, track_status, schedule)

    assert len(panel) == 3
    assert list(panel["Lap"]) == [1, 2, 3]
    assert (panel["CircuitId"] == "monza").all()
    assert list(panel["RaceLength"]) == [3, 3, 3]
    assert panel.iloc[0]["LapFraction"] == 1 / 3
    assert panel.iloc[2]["LapFraction"] == 1.0


def test_build_hazard_panel_flags_is_lap_one():
    laps = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "LapNumber": [1, 2],
            "LapStartTime": [pd.Timedelta(seconds=0), pd.Timedelta(seconds=90)],
        }
    )
    track_status = pd.DataFrame(
        {"Season": [2023], "Round": [1], "Time": [pd.Timedelta(seconds=0)], "Status": ["1"]}
    )
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["monza"]})

    panel = features.build_hazard_panel(laps, track_status, schedule)

    assert list(panel["IsLapOne"]) == [1, 0]


def test_build_hazard_panel_marks_event_lap_and_increments_incidents_so_far():
    laps = pd.DataFrame(
        {
            "Season": [2023] * 4,
            "Round": [1] * 4,
            "LapNumber": [1, 2, 3, 4],
            "LapStartTime": [
                pd.Timedelta(seconds=0),
                pd.Timedelta(seconds=90),
                pd.Timedelta(seconds=180),
                pd.Timedelta(seconds=270),
            ],
        }
    )
    track_status = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023, 2023],
            "Round": [1, 1, 1, 1],
            "Time": [
                pd.Timedelta(seconds=0),
                pd.Timedelta(seconds=185),
                pd.Timedelta(seconds=200),
                pd.Timedelta(seconds=280),
            ],
            # a clear ("1") between the two hazard codes is required for them to
            # register as two separate events -- "4" directly followed by "6"
            # with no intervening clear is one continuous hazard run, not two.
            "Status": ["1", "4", "1", "6"],
        }
    )
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["monza"]})

    panel = features.build_hazard_panel(laps, track_status, schedule)

    assert list(panel["Event"]) == [0, 0, 1, 1]
    # IncidentsSoFar counts events strictly before this lap, not including it
    assert list(panel["IncidentsSoFar"]) == [0, 0, 0, 1]


def test_build_hazard_panel_skips_races_missing_from_schedule():
    laps = pd.DataFrame(
        {
            "Season": [2023],
            "Round": [1],
            "LapNumber": [1],
            "LapStartTime": [pd.Timedelta(seconds=0)],
        }
    )
    track_status = pd.DataFrame(
        {"Season": [2023], "Round": [1], "Time": [pd.Timedelta(seconds=0)], "Status": ["1"]}
    )
    schedule = pd.DataFrame(columns=["Season", "Round", "CircuitId"])

    panel = features.build_hazard_panel(laps, track_status, schedule)

    assert len(panel) == 0
