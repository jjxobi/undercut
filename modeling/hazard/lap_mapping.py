from __future__ import annotations

import numpy as np
import pandas as pd

HAZARD_STATUS_CODES = {"4", "6"}


def build_race_clock(laps: pd.DataFrame) -> pd.DataFrame:
    clock = (
        laps.groupby(["Season", "Round", "LapNumber"])["LapStartTime"]
        .median()
        .reset_index()
        .dropna(subset=["LapStartTime"])
    )
    return clock.sort_values(["Season", "Round", "LapNumber"]).reset_index(drop=True)


def hazard_event_starts(track_status: pd.DataFrame) -> pd.DataFrame:
    status = track_status.sort_values(["Season", "Round", "Time"]).reset_index(drop=True).copy()
    status["IsHazard"] = status["Status"].astype(str).isin(HAZARD_STATUS_CODES)
    status["GroupKey"] = list(zip(status["Season"], status["Round"]))
    status["Changed"] = (
        status["IsHazard"] != status.groupby("GroupKey")["IsHazard"].shift()
    ).astype(int)
    status["EventId"] = status.groupby("GroupKey")["Changed"].cumsum()

    hazard_rows = status[status["IsHazard"]]
    starts = (
        hazard_rows.groupby(["Season", "Round", "EventId"])
        .first()
        .reset_index()[["Season", "Round", "Time"]]
    )
    return starts.reset_index(drop=True)


def map_events_to_laps(event_starts: pd.DataFrame, race_clock: pd.DataFrame) -> pd.DataFrame:
    mapped = []
    for (season, round_number), events in event_starts.groupby(["Season", "Round"]):
        race_clock_rows = race_clock[
            (race_clock["Season"] == season) & (race_clock["Round"] == round_number)
        ]
        if len(race_clock_rows) == 0:
            continue
        lap_starts = race_clock_rows["LapStartTime"].to_numpy()
        lap_numbers = race_clock_rows["LapNumber"].to_numpy()
        for event_time in events["Time"].to_numpy():
            index = np.searchsorted(lap_starts, event_time, side="right") - 1
            index = max(0, min(index, len(lap_numbers) - 1))
            mapped.append(
                {"Season": season, "Round": round_number, "Lap": int(lap_numbers[index])}
            )

    return pd.DataFrame(mapped, columns=["Season", "Round", "Lap"])
