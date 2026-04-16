import pandas as pd

from modeling.hazard import lap_mapping


def test_build_race_clock_takes_median_lap_start_time_across_drivers():
    laps = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023, 2023],
            "Round": [1, 1, 1, 1],
            "LapNumber": [1, 1, 2, 2],
            "LapStartTime": [
                pd.Timedelta(seconds=0),
                pd.Timedelta(seconds=2),
                pd.Timedelta(seconds=90),
                pd.Timedelta(seconds=94),
            ],
        }
    )

    clock = lap_mapping.build_race_clock(laps)

    lap1 = clock[clock["LapNumber"] == 1].iloc[0]
    lap2 = clock[clock["LapNumber"] == 2].iloc[0]
    assert lap1["LapStartTime"] == pd.Timedelta(seconds=1)
    assert lap2["LapStartTime"] == pd.Timedelta(seconds=92)


def test_build_race_clock_drops_missing_lap_start_times():
    laps = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "LapNumber": [1, 2],
            "LapStartTime": [pd.Timedelta(seconds=0), pd.NaT],
        }
    )

    clock = lap_mapping.build_race_clock(laps)

    assert list(clock["LapNumber"]) == [1]


def test_build_race_clock_is_monotonically_nondecreasing_within_a_race():
    laps = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023],
            "Round": [1, 1, 1],
            "LapNumber": [1, 2, 3],
            "LapStartTime": [
                pd.Timedelta(seconds=0),
                pd.Timedelta(seconds=90),
                pd.Timedelta(seconds=85),  # artifact: earlier than lap 2's start
            ],
        }
    )

    clock = lap_mapping.build_race_clock(laps)

    assert clock["LapStartTime"].is_monotonic_increasing or (
        clock["LapStartTime"].diff().dropna() >= pd.Timedelta(0)
    ).all()


def test_hazard_event_starts_finds_one_row_per_contiguous_hazard_run():
    status = pd.DataFrame(
        {
            "Season": [2023] * 6,
            "Round": [1] * 6,
            "Time": [pd.Timedelta(minutes=m) for m in range(6)],
            "Status": ["1", "4", "4", "1", "6", "1"],
        }
    )

    starts = lap_mapping.hazard_event_starts(status)

    assert len(starts) == 2
    assert list(starts["Time"]) == [pd.Timedelta(minutes=1), pd.Timedelta(minutes=4)]


def test_hazard_event_starts_handles_multiple_races_independently():
    status = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023, 2023],
            "Round": [1, 1, 2, 2],
            "Time": [pd.Timedelta(minutes=m) for m in range(4)],
            "Status": ["4", "1", "1", "6"],
        }
    )

    starts = lap_mapping.hazard_event_starts(status)

    assert len(starts) == 2
    assert set(zip(starts["Season"], starts["Round"])) == {(2023, 1), (2023, 2)}


def test_map_events_to_laps_finds_containing_lap():
    race_clock = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023],
            "Round": [1, 1, 1],
            "LapNumber": [1, 2, 3],
            "LapStartTime": [
                pd.Timedelta(seconds=0),
                pd.Timedelta(seconds=90),
                pd.Timedelta(seconds=180),
            ],
        }
    )
    event_starts = pd.DataFrame(
        {"Season": [2023], "Round": [1], "Time": [pd.Timedelta(seconds=95)]}
    )

    mapped = lap_mapping.map_events_to_laps(event_starts, race_clock)

    assert len(mapped) == 1
    assert mapped.iloc[0]["Lap"] == 2


def test_map_events_to_laps_clamps_event_before_first_lap_start_to_lap_one():
    race_clock = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "LapNumber": [1, 2],
            "LapStartTime": [pd.Timedelta(seconds=10), pd.Timedelta(seconds=100)],
        }
    )
    event_starts = pd.DataFrame(
        {"Season": [2023], "Round": [1], "Time": [pd.Timedelta(seconds=5)]}
    )

    mapped = lap_mapping.map_events_to_laps(event_starts, race_clock)

    assert mapped.iloc[0]["Lap"] == 1


def test_map_events_to_laps_clamps_event_after_last_lap_start_to_last_lap():
    race_clock = pd.DataFrame(
        {
            "Season": [2023, 2023],
            "Round": [1, 1],
            "LapNumber": [1, 2],
            "LapStartTime": [pd.Timedelta(seconds=0), pd.Timedelta(seconds=90)],
        }
    )
    event_starts = pd.DataFrame(
        {"Season": [2023], "Round": [1], "Time": [pd.Timedelta(seconds=500)]}
    )

    mapped = lap_mapping.map_events_to_laps(event_starts, race_clock)

    assert mapped.iloc[0]["Lap"] == 2


def test_map_events_to_laps_skips_races_with_no_race_clock():
    race_clock = pd.DataFrame(columns=["Season", "Round", "LapNumber", "LapStartTime"])
    event_starts = pd.DataFrame(
        {"Season": [2023], "Round": [1], "Time": [pd.Timedelta(seconds=5)]}
    )

    mapped = lap_mapping.map_events_to_laps(event_starts, race_clock)

    assert len(mapped) == 0
