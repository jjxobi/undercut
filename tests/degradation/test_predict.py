import pandas as pd
import pytest

from modeling.degradation import predict


def test_degradation_seconds_is_zero_at_tyre_life_one():
    result = predict.degradation_seconds(tyre_life=1, tyre_life_coef=0.08, tyre_life_squared_coef=0.002)

    assert result == pytest.approx(0.0)


def test_degradation_seconds_increases_with_tyre_age():
    at_five = predict.degradation_seconds(tyre_life=5, tyre_life_coef=0.08, tyre_life_squared_coef=0.002)
    at_fifteen = predict.degradation_seconds(tyre_life=15, tyre_life_coef=0.08, tyre_life_squared_coef=0.002)

    assert at_five > 0
    assert at_fifteen > at_five


def _coefficients():
    return pd.DataFrame(
        [
            {"compound": "MEDIUM", "scope": "circuit", "circuit_id": "bahrain",
             "tyre_life_coef": 0.08, "tyre_life_squared_coef": 0.002},
            {"compound": "MEDIUM", "scope": "pooled", "circuit_id": None,
             "tyre_life_coef": 0.10, "tyre_life_squared_coef": 0.001},
            {"compound": "SOFT", "scope": "pooled", "circuit_id": None,
             "tyre_life_coef": 0.15, "tyre_life_squared_coef": 0.003},
        ]
    )


def test_lookup_coefficients_prefers_circuit_specific_model():
    row = predict.lookup_coefficients(_coefficients(), compound="MEDIUM", circuit_id="bahrain")

    assert row["scope"] == "circuit"
    assert row["tyre_life_coef"] == 0.08


def test_lookup_coefficients_falls_back_to_pooled_when_no_circuit_model():
    row = predict.lookup_coefficients(_coefficients(), compound="MEDIUM", circuit_id="monaco")

    assert row["scope"] == "pooled"
    assert row["tyre_life_coef"] == 0.10


def test_lookup_coefficients_raises_when_compound_has_no_model_at_all():
    with pytest.raises(ValueError, match="WET"):
        predict.lookup_coefficients(_coefficients(), compound="WET", circuit_id="bahrain")
