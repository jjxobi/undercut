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


def test_degradation_seconds_clamps_at_peak_for_concave_curve():
    # c2 < 0 means the fitted curve rises to a peak (vertex = -c1/(2*c2), here
    # t=25) and then declines -- a real but unreliable extrapolation far past
    # the observed data. Querying past the vertex should hold flat at the
    # vertex's value rather than follow the curve back down.
    coef, squared_coef = 0.1, -0.002
    vertex_tyre_life = -coef / (2 * squared_coef)
    assert vertex_tyre_life == pytest.approx(25.0)

    at_vertex = predict.degradation_seconds(vertex_tyre_life, coef, squared_coef)
    at_sixty = predict.degradation_seconds(60, coef, squared_coef)

    assert at_sixty == pytest.approx(at_vertex)
    assert at_sixty >= 0


def test_degradation_seconds_floors_at_zero_for_early_dip():
    # c2 > 0 with c1 < 0 means the curve genuinely dips below the fresh-tyre
    # baseline for early tyre life before recovering and rising (the "gets
    # faster before it degrades" pattern seen in real data) -- during the dip,
    # degradation_seconds should report 0.0 ("no measurable degradation")
    # rather than a negative number, and should stay non-negative throughout.
    coef, squared_coef = -0.05, 0.002

    at_ten = predict.degradation_seconds(10, coef, squared_coef)
    assert at_ten == pytest.approx(0.0)

    values = [predict.degradation_seconds(t, coef, squared_coef) for t in range(1, 41)]
    assert all(v >= 0 for v in values)
    assert any(v > 0 for v in values)


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
