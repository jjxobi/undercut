from itertools import pairwise

import pandas as pd

from modeling.optimization import degradation_lookup


def _coefficients() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "era": "2018-2021 aero",
                "compound": "MEDIUM",
                "scope": "circuit",
                "circuit_id": "bahrain",
                "tyre_life_coef": 0.08,
                "tyre_life_squared_coef": 0.0,
            }
        ]
    )


def test_build_cumulative_cost_table_starts_at_zero():
    table = degradation_lookup.build_cumulative_cost_table(
        "MEDIUM", "bahrain", "2018-2021 aero", 10, _coefficients()
    )

    assert table[0] == 0


def test_build_cumulative_cost_table_is_nondecreasing():
    table = degradation_lookup.build_cumulative_cost_table(
        "MEDIUM", "bahrain", "2018-2021 aero", 10, _coefficients()
    )

    assert all(b >= a for a, b in pairwise(table))


def test_build_cumulative_cost_table_has_max_tyre_life_plus_one_entries():
    table = degradation_lookup.build_cumulative_cost_table(
        "MEDIUM", "bahrain", "2018-2021 aero", 10, _coefficients()
    )

    assert len(table) == 11


def test_build_cumulative_cost_table_matches_hand_computed_value():
    # c1=0.08, c2=0.0: degradation_seconds(t) = 0.08*(t-1) for each lap (linear,
    # baseline-subtracted at t=1). Cumulative at tyre life 3 = sum of
    # degradation_seconds(1) + degradation_seconds(2) + degradation_seconds(3)
    # = 0 + 0.08 + 0.16 = 0.24s = 24 centiseconds.
    table = degradation_lookup.build_cumulative_cost_table(
        "MEDIUM", "bahrain", "2018-2021 aero", 10, _coefficients()
    )

    assert table[3] == 24
