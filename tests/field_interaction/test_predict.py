import pandas as pd
import pytest

from modeling.field_interaction import predict


def _coefficients() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"circuit_id": None, "n_races": 3700, "mean_position_delta": -0.22, "position_delta_sd": 5.26},
            {"circuit_id": "monaco", "n_races": 162, "mean_position_delta": 0.0, "position_delta_sd": 4.55},
        ]
    )


def test_position_volatility_returns_circuit_specific_row_when_available():
    row = predict.position_volatility("monaco", _coefficients())

    assert row["position_delta_sd"] == 4.55


def test_position_volatility_falls_back_to_population_for_unseen_circuit():
    row = predict.position_volatility("a_brand_new_2027_venue", _coefficients())

    assert row["position_delta_sd"] == 5.26


def test_position_volatility_raises_when_no_population_row_and_circuit_unknown():
    coefficients = _coefficients()
    coefficients = coefficients[coefficients["circuit_id"].notna()]

    with pytest.raises(ValueError, match="no position-volatility model"):
        predict.position_volatility("unknown_circuit", coefficients)
