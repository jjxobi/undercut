from __future__ import annotations

import pandas as pd


def build_position_change_frame(results: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    frame = results.merge(
        schedule[["Season", "Round", "CircuitId"]], on=["Season", "Round"], how="inner"
    )
    frame = frame.dropna(subset=["GridPosition", "Position", "CircuitId"]).copy()
    frame["PositionDelta"] = frame["GridPosition"] - frame["Position"]
    return frame
