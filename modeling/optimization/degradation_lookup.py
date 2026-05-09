from __future__ import annotations

import pandas as pd

from modeling.degradation import predict as degradation_predict

CENTISECONDS_PER_SECOND = 100


def build_cumulative_cost_table(
    compound: str,
    circuit_id: str,
    era: str,
    max_tyre_life: int,
    degradation_coefficients: pd.DataFrame,
) -> list[int]:
    row = degradation_predict.lookup_coefficients(degradation_coefficients, compound, circuit_id, era)
    tyre_life_coef = row["tyre_life_coef"]
    tyre_life_squared_coef = row["tyre_life_squared_coef"]

    cumulative = [0]
    running_total_seconds = 0.0
    for tyre_life in range(1, max_tyre_life + 1):
        running_total_seconds += degradation_predict.degradation_seconds(
            tyre_life, tyre_life_coef, tyre_life_squared_coef
        )
        cumulative.append(round(running_total_seconds * CENTISECONDS_PER_SECOND))
    return cumulative
