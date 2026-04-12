import pandas as pd
import pytest

from modeling.hazard import predict


def _coefficients() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"circuit_id": None, "intercept": -3.8, "is_lap_one_coef": 2.5,
             "lap_fraction_coef": -0.4, "incidents_so_far_coef": 0.05},
            {"circuit_id": "monza", "intercept": -4.0, "is_lap_one_coef": 2.5,
             "lap_fraction_coef": -0.4, "incidents_so_far_coef": 0.05},
        ]
    )


def test_hazard_probability_is_between_zero_and_one():
    probability = predict.hazard_probability(
        lap=10, race_length=55, incidents_so_far=0, circuit_id="monza",
        coefficients=_coefficients(),
    )

    assert 0.0 < probability < 1.0


def test_hazard_probability_is_higher_on_lap_one():
    lap_one = predict.hazard_probability(
        lap=1, race_length=55, incidents_so_far=0, circuit_id="monza",
        coefficients=_coefficients(),
    )
    lap_ten = predict.hazard_probability(
        lap=10, race_length=55, incidents_so_far=0, circuit_id="monza",
        coefficients=_coefficients(),
    )

    assert lap_one > lap_ten


def test_hazard_probability_uses_circuit_specific_row_when_available():
    monza = predict.hazard_probability(
        lap=10, race_length=55, incidents_so_far=0, circuit_id="monza",
        coefficients=_coefficients(),
    )
    population = predict.hazard_probability(
        lap=10, race_length=55, incidents_so_far=0, circuit_id="unknown_circuit",
        coefficients=_coefficients(),
    )

    assert monza != population


def test_hazard_probability_falls_back_to_population_for_unseen_circuit():
    probability = predict.hazard_probability(
        lap=10, race_length=55, incidents_so_far=0, circuit_id="a_brand_new_2027_venue",
        coefficients=_coefficients(),
    )

    assert 0.0 < probability < 1.0


def test_hazard_probability_raises_when_no_population_row_and_circuit_unknown():
    coefficients = _coefficients()
    coefficients = coefficients[coefficients["circuit_id"].notna()]

    with pytest.raises(ValueError, match="no hazard model"):
        predict.hazard_probability(
            lap=10, race_length=55, incidents_so_far=0, circuit_id="unknown_circuit",
            coefficients=coefficients,
        )
