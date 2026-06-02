from __future__ import annotations

import pandas as pd

MIN_OBSERVATIONS = 20


def estimate_seconds_per_position(laps: pd.DataFrame, results: pd.DataFrame) -> float:
    finished = results[results["Status"].eq("Finished") | results["Status"].str.contains("Lap", na=False)]
    finished_keys = finished[["Season", "Round", "Code"]].rename(columns={"Code": "Driver"})

    last_laps = (
        laps.sort_values(["Season", "Round", "Driver", "LapNumber"])
        .groupby(["Season", "Round", "Driver"])
        .tail(1)
        .dropna(subset=["Time", "Position", "LapNumber"])
    )
    last_laps = last_laps.merge(finished_keys, on=["Season", "Round", "Driver"], how="inner")

    gaps = []
    for _, race_group in last_laps.groupby(["Season", "Round"]):
        ordered = race_group.sort_values("Position")
        lap_numbers = ordered["LapNumber"].to_numpy()
        times = ordered["Time"].dt.total_seconds().to_numpy()
        for i in range(len(ordered) - 1):
            if lap_numbers[i] == lap_numbers[i + 1]:
                gaps.append(times[i + 1] - times[i])

    if len(gaps) < MIN_OBSERVATIONS:
        raise ValueError(
            f"only {len(gaps)} same-lap adjacent-position observations available, "
            f"need at least {MIN_OBSERVATIONS} to estimate a reliable gap"
        )

    return float(pd.Series(gaps).median())
