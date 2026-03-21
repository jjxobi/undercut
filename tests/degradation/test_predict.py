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
            {"compound": "MEDIUM", "scope": "circuit", "circuit_id": "bahrain", "era": "2022-2025 ground-effect",
             "tyre_life_coef": 0.08, "tyre_life_squared_coef": 0.002},
            {"compound": "MEDIUM", "scope": "pooled", "circuit_id": None, "era": "2022-2025 ground-effect",
             "tyre_life_coef": 0.10, "tyre_life_squared_coef": 0.001},
            {"compound": "SOFT", "scope": "pooled", "circuit_id": None, "era": "2022-2025 ground-effect",
             "tyre_life_coef": 0.15, "tyre_life_squared_coef": 0.003},
        ]
    )


def test_lookup_coefficients_prefers_circuit_specific_model():
    row = predict.lookup_coefficients(
        _coefficients(), compound="MEDIUM", circuit_id="bahrain", era="2022-2025 ground-effect"
    )

    assert row["scope"] == "circuit"
    assert row["tyre_life_coef"] == 0.08


def test_lookup_coefficients_falls_back_to_pooled_when_no_circuit_model():
    row = predict.lookup_coefficients(
        _coefficients(), compound="MEDIUM", circuit_id="monaco", era="2022-2025 ground-effect"
    )

    assert row["scope"] == "pooled"
    assert row["tyre_life_coef"] == 0.10


def test_lookup_coefficients_raises_when_compound_has_no_model_at_all():
    with pytest.raises(ValueError, match="WET"):
        predict.lookup_coefficients(
            _coefficients(), compound="WET", circuit_id="bahrain", era="2022-2025 ground-effect"
        )


def test_lookup_coefficients_does_not_match_wrong_era():
    # bahrain's circuit-specific row only exists for 2022-2025 ground-effect, and
    # there's no pooled row for 2018-2021 aero either -- a lookup for the wrong
    # era must not silently return another era's circuit-specific model, since
    # regulation changes (e.g. the 2022 ground-effect/18-inch-tyre switch) mean
    # degradation behavior isn't comparable across eras.
    with pytest.raises(ValueError, match="MEDIUM"):
        predict.lookup_coefficients(
            _coefficients(), compound="MEDIUM", circuit_id="bahrain", era="2018-2021 aero"
        )
