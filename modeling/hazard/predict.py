from __future__ import annotations

import numpy as np
import pandas as pd


def hazard_probability(
    lap: int,
    race_length: int,
    incidents_so_far: int,
    circuit_id: str,
    coefficients: pd.DataFrame,
) -> float:
    circuit_match = coefficients[coefficients["circuit_id"] == circuit_id]
    if len(circuit_match) > 0:
        row = circuit_match.iloc[0]
    else:
        population_match = coefficients[coefficients["circuit_id"].isna()]
        if len(population_match) == 0:
            raise ValueError(f"no hazard model available for circuit_id={circuit_id}")
        row = population_match.iloc[0]

    is_lap_one = 1 if lap == 1 else 0
    lap_fraction = lap / race_length
    log_odds = (
        row["intercept"]
        + row["is_lap_one_coef"] * is_lap_one
        + row["lap_fraction_coef"] * lap_fraction
        + row["incidents_so_far_coef"] * incidents_so_far
    )
    return float(1.0 / (1.0 + np.exp(-log_odds)))
