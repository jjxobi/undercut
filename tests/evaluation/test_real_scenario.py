import pandas as pd

from modeling.evaluation import real_scenario


def test_build_real_scenario_flags_a_lap_if_any_driver_reports_a_hazard_code():
    laps = pd.DataFrame(
        [
            {"Season": 2023, "Round": 1, "Driver": "VER", "LapNumber": 1, "TrackStatus": "1"},
            {"Season": 2023, "Round": 1, "Driver": "HAM", "LapNumber": 1, "TrackStatus": "1"},
            {"Season": 2023, "Round": 1, "Driver": "VER", "LapNumber": 2, "TrackStatus": "1"},
            # HAM alone caught a status change to VSC (code "4") partway through lap 2
            {"Season": 2023, "Round": 1, "Driver": "HAM", "LapNumber": 2, "TrackStatus": "14"},
            {"Season": 2023, "Round": 1, "Driver": "VER", "LapNumber": 3, "TrackStatus": "1"},
            {"Season": 2023, "Round": 1, "Driver": "HAM", "LapNumber": 3, "TrackStatus": "1"},
        ]
    )

    scenario = real_scenario.build_real_scenario(laps, 2023, 1, race_length=3)

    assert scenario == [False, True, False]


def test_build_real_scenario_ignores_other_races():
    laps = pd.DataFrame(
        [
            {"Season": 2023, "Round": 1, "Driver": "VER", "LapNumber": 1, "TrackStatus": "4"},
            {"Season": 2023, "Round": 2, "Driver": "VER", "LapNumber": 1, "TrackStatus": "1"},
        ]
    )

    scenario = real_scenario.build_real_scenario(laps, 2023, 2, race_length=1)

    assert scenario == [False]


def test_build_real_scenario_ignores_lap_numbers_past_race_length():
    # a lapped car's final "lap" can be recorded past the winner's race length
    # in some FastF1 sessions -- must not overrun the returned list
    laps = pd.DataFrame(
        [
            {"Season": 2023, "Round": 1, "Driver": "VER", "LapNumber": 1, "TrackStatus": "1"},
            {"Season": 2023, "Round": 1, "Driver": "VER", "LapNumber": 2, "TrackStatus": "6"},
        ]
    )

    scenario = real_scenario.build_real_scenario(laps, 2023, 1, race_length=1)

    assert scenario == [False]
