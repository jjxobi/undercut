import numpy as np
import pandas as pd

from modeling.optimization import scenarios


def _coefficients_always_hazard() -> pd.DataFrame:
    # a hazard coefficient set that always predicts probability ~1 on lap 1 and
    # ~0 afterward, so scenario sampling is deterministic enough to test
    return pd.DataFrame(
        [
            {
                "circuit_id": None,
                "is_latest": True,
                "intercept": 100.0,
                "is_lap_one_coef": 0.0,
                "lap_fraction_coef": -1000.0,
                "incidents_so_far_coef": 0.0,
            }
        ]
    )


def test_sample_scenario_produces_one_entry_per_lap():
    rng = np.random.default_rng(1)
    scenario = scenarios.sample_scenario(20, "bahrain", "2018-2021 aero", _coefficients_always_hazard(), [3], rng)

    assert len(scenario) == 20


def test_sample_scenario_marks_a_hazard_active_for_its_full_duration():
    # forced-hazard coefficients + a fixed 3-lap duration -- lap 1 must trigger
    # a hazard that stays active laps 1-3, then (given the coefficients decay
    # hazard probability toward 0 as the race progresses) very likely clear
    rng = np.random.default_rng(1)
    scenario = scenarios.sample_scenario(20, "bahrain", "2018-2021 aero", _coefficients_always_hazard(), [3], rng)

    assert scenario[0] and scenario[1] and scenario[2]  # laps 1-3 (0-indexed 0,1,2)


def test_sample_scenarios_produces_the_requested_count():
    result = scenarios.sample_scenarios(
        5, 20, "bahrain", "2018-2021 aero", _coefficients_always_hazard(), [2], seed=7
    )

    assert len(result) == 5
    assert all(len(s) == 20 for s in result)


def test_sample_scenarios_is_reproducible_with_the_same_seed():
    first = scenarios.sample_scenarios(3, 30, "monza", "2022-2025 ground-effect", _coefficients_always_hazard(), [1, 2, 3], seed=42)
    second = scenarios.sample_scenarios(3, 30, "monza", "2022-2025 ground-effect", _coefficients_always_hazard(), [1, 2, 3], seed=42)

    assert first == second
