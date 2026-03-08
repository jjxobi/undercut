from __future__ import annotations

import pandas as pd


def add_circuit(laps: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    return laps.merge(schedule[["Season", "Round", "CircuitId"]], on=["Season", "Round"], how="left")


def add_weather(laps: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for (season, round_number), group in laps.groupby(["Season", "Round"], sort=False):
        race_weather = (
            weather[(weather["Season"] == season) & (weather["Round"] == round_number)]
            .sort_values("Time")
        )
        race_laps = group.sort_values("Time")
        merged = pd.merge_asof(
            race_laps,
            race_weather[["Time", "TrackTemp", "AirTemp", "Rainfall"]],
            on="Time",
            direction="nearest",
        )
        parts.append(merged)
    return pd.concat(parts, ignore_index=True) if parts else laps.copy()


def build_training_frame(laps: pd.DataFrame, schedule: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    frame = add_circuit(laps, schedule)
    frame = add_weather(frame, weather)
    frame["LapTimeSeconds"] = frame["LapTime"].dt.total_seconds()
    frame["TyreLifeSquared"] = frame["TyreLife"] ** 2
    frame["RaceLapNumber"] = frame["LapNumber"]
    return frame
