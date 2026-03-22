from __future__ import annotations

import pandas as pd

_BASELINE_TYRE_LIFE = 1


def degradation_seconds(tyre_life: float, tyre_life_coef: float, tyre_life_squared_coef: float) -> float:
    if tyre_life_squared_coef < 0:
        vertex = -tyre_life_coef / (2 * tyre_life_squared_coef)
        effective_tyre_life = min(tyre_life, max(vertex, _BASELINE_TYRE_LIFE))
    else:
        effective_tyre_life = tyre_life
    baseline = tyre_life_coef * _BASELINE_TYRE_LIFE + tyre_life_squared_coef * _BASELINE_TYRE_LIFE**2
    at_tyre_life = tyre_life_coef * effective_tyre_life + tyre_life_squared_coef * effective_tyre_life**2
    return max(0.0, at_tyre_life - baseline)


def lookup_coefficients(coefficients: pd.DataFrame, compound: str, circuit_id: str, era: str) -> pd.Series:
    circuit_match = coefficients[
        (coefficients["compound"] == compound)
        & (coefficients["scope"] == "circuit")
        & (coefficients["circuit_id"] == circuit_id)
        & (coefficients["era"] == era)
    ]
    if len(circuit_match) > 0:
        return circuit_match.iloc[0]

    pooled_match = coefficients[
        (coefficients["compound"] == compound)
        & (coefficients["scope"] == "pooled")
        & (coefficients["era"] == era)
    ]
    if len(pooled_match) > 0:
        return pooled_match.iloc[0]

    raise ValueError(f"no degradation model available for compound={compound} era={era}")
