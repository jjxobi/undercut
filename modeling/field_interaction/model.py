from __future__ import annotations

import numpy as np
import pandas as pd

SHRINKAGE_STRENGTH = 5.0

RESULT_COLUMNS = ["circuit_id", "n_races", "mean_position_delta", "position_delta_sd"]


def fit_position_volatility(frame: pd.DataFrame) -> pd.DataFrame:
    population_variance = float(frame["PositionDelta"].var())

    records = [
        {
            "circuit_id": None,
            "n_races": len(frame),
            "mean_position_delta": float(frame["PositionDelta"].mean()),
            "position_delta_sd": float(np.sqrt(population_variance)),
        }
    ]

    for circuit_id, circuit_frame in frame.groupby("CircuitId"):
        n_races = len(circuit_frame)
        circuit_variance = float(circuit_frame["PositionDelta"].var()) if n_races > 1 else population_variance
        if pd.isna(circuit_variance):
            circuit_variance = population_variance
        shrunk_variance = (
            n_races * circuit_variance + SHRINKAGE_STRENGTH * population_variance
        ) / (n_races + SHRINKAGE_STRENGTH)
        records.append(
            {
                "circuit_id": circuit_id,
                "n_races": n_races,
                "mean_position_delta": float(circuit_frame["PositionDelta"].mean()),
                "position_delta_sd": float(np.sqrt(shrunk_variance)),
            }
        )

    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
