import numpy as np
import pandas as pd

from modeling.field_interaction import position_outcomes


def test_build_position_change_frame_computes_delta():
    results = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "Driver": ["max_verstappen", "hamilton"],
            "Position": [1, 3],
            "Status": ["Finished", "Finished"],
            "GridPosition": [1, 5],
        }
    )
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]})

    frame = position_outcomes.build_position_change_frame(results, schedule)

    assert list(frame["PositionDelta"]) == [0, 2]
    assert (frame["CircuitId"] == "bahrain").all()


def test_build_position_change_frame_drops_rows_missing_grid_or_finish_position():
    results = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "Driver": ["max_verstappen", "hamilton"],
            "Position": [1, np.nan],
            "Status": ["Finished", "Finished"],
            "GridPosition": [1, 5],
        }
    )
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]})

    frame = position_outcomes.build_position_change_frame(results, schedule)

    assert len(frame) == 1
    assert frame.iloc[0]["Driver"] == "max_verstappen"


def test_build_position_change_frame_drops_races_missing_from_schedule():
    results = pd.DataFrame(
        {
            "Season": [2023],
            "Round": [1],
            "Driver": ["max_verstappen"],
            "Position": [1],
            "Status": ["Finished"],
            "GridPosition": [1],
        }
    )
    schedule = pd.DataFrame(columns=["Season", "Round", "CircuitId"])

    frame = position_outcomes.build_position_change_frame(results, schedule)

    assert len(frame) == 0


def test_build_position_change_frame_drops_pit_lane_starts():
    results = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "Driver": ["max_verstappen", "hamilton"],
            "Position": [1, 15],
            "Status": ["Finished", "Finished"],
            "GridPosition": [1, 0],  # hamilton started from the pit lane
        }
    )
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]})

    frame = position_outcomes.build_position_change_frame(results, schedule)

    assert len(frame) == 1
    assert frame.iloc[0]["Driver"] == "max_verstappen"


def test_build_position_change_frame_drops_non_finishers():
    results = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023],
            "Driver": ["max_verstappen", "hamilton", "perez"],
            "Round": [1, 1, 1],
            "Position": [1, 10, 15],
            "Status": ["Finished", "+1 Lap", "Retired"],
            "GridPosition": [1, 5, 8],
        }
    )
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]})

    frame = position_outcomes.build_position_change_frame(results, schedule)

    assert set(frame["Driver"]) == {"max_verstappen", "hamilton"}
