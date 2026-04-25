from __future__ import annotations

import pandas as pd


def position_volatility(circuit_id: str, coefficients: pd.DataFrame) -> pd.Series:
    circuit_match = coefficients[coefficients["circuit_id"] == circuit_id]
    if len(circuit_match) > 0:
        return circuit_match.iloc[0]

    population_match = coefficients[coefficients["circuit_id"].isna()]
    if len(population_match) == 0:
        raise ValueError(f"no position-volatility model available for circuit_id={circuit_id}")
    return population_match.iloc[0]
