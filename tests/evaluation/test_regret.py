import pandas as pd

from modeling.evaluation import regret


def _degradation_coefficients() -> pd.DataFrame:
    rows = []
    for compound, coef in [("SOFT", 0.20), ("MEDIUM", 0.10), ("HARD", 0.05)]:
        rows.append(
            {
                "era": "2018-2021 aero",
                "compound": compound,
                "scope": "pooled",
                "circuit_id": None,
                "tyre_life_coef": coef,
                "tyre_life_squared_coef": 0.0,
            }
        )
    return pd.DataFrame(rows)


def _hazard_coefficients() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "circuit_id": None,
                "variant_id": None,
                "is_latest": False,
                "intercept": -3.8,
                "is_lap_one_coef": 2.5,
                "lap_fraction_coef": -0.4,
                "incidents_so_far_coef": 0.0,
            }
        ]
    )


def test_compute_race_benchmarks_returns_a_cost_for_each_plan():
    real_scenario = [False] * 8 + [True] * 3 + [False] * 9  # a 20-lap race, SC on laps 9-11

    benchmarks = regret.compute_race_benchmarks(
        season=2023,
        round_number=1,
        circuit_id="bahrain",
        era="2018-2021 aero",
        race_length=20,
        real_scenario=real_scenario,
        degradation_coefficients=_degradation_coefficients(),
        hazard_coefficients=_hazard_coefficients(),
        pit_loss_seconds=24.0,
        n_scenarios=5,
        policy_seed=11,
    )

    assert isinstance(benchmarks["oracle_cost_seconds"], float)
    assert isinstance(benchmarks["policy_cost_seconds"], float)
    assert benchmarks["oracle_compounds"] in [
        ["MEDIUM", "HARD"], ["SOFT", "HARD"], ["SOFT", "MEDIUM"],
        ["SOFT", "MEDIUM", "HARD"], ["MEDIUM", "HARD", "MEDIUM"],
    ]


def test_compute_race_benchmarks_oracle_never_costs_more_than_policy_on_the_real_scenario():
    # the oracle sees the exact real scenario in advance; the policy only saw
    # scenarios sampled before the fact -- on the real outcome, the oracle's
    # own search (same candidate sequences, same real scenario) can never be
    # beaten by a plan chosen without that foreknowledge
    real_scenario = [False] * 5 + [True] * 3 + [False] * 12

    benchmarks = regret.compute_race_benchmarks(
        season=2023,
        round_number=1,
        circuit_id="bahrain",
        era="2018-2021 aero",
        race_length=20,
        real_scenario=real_scenario,
        degradation_coefficients=_degradation_coefficients(),
        hazard_coefficients=_hazard_coefficients(),
        pit_loss_seconds=24.0,
        n_scenarios=20,
        policy_seed=3,
    )

    assert benchmarks["oracle_cost_seconds"] <= benchmarks["policy_cost_seconds"] + 1e-9


def test_price_actual_strategy_matches_the_oracle_cost_when_it_is_the_oracle_plan():
    real_scenario = [False] * 20

    benchmarks = regret.compute_race_benchmarks(
        season=2023,
        round_number=1,
        circuit_id="bahrain",
        era="2018-2021 aero",
        race_length=20,
        real_scenario=real_scenario,
        degradation_coefficients=_degradation_coefficients(),
        hazard_coefficients=_hazard_coefficients(),
        pit_loss_seconds=24.0,
        n_scenarios=5,
        policy_seed=1,
    )

    priced = regret.price_actual_strategy(
        benchmarks["oracle_compounds"],
        benchmarks["oracle_stint_lengths"],
        circuit_id="bahrain",
        era="2018-2021 aero",
        race_length=20,
        degradation_coefficients=_degradation_coefficients(),
        real_scenario=real_scenario,
        pit_loss_seconds=24.0,
    )

    assert priced == benchmarks["oracle_cost_seconds"]
