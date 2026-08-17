import pandas as pd

from modeling.optimization import comparison


def _synthetic_coefficients():
    degradation_rows = []
    for compound, coef in [("SOFT", 0.20), ("MEDIUM", 0.10), ("HARD", 0.05)]:
        degradation_rows.append(
            {
                "era": "2018-2021 aero",
                "compound": compound,
                "scope": "pooled",
                "circuit_id": None,
                "tyre_life_coef": coef,
                "tyre_life_squared_coef": 0.0,
            }
        )
    degradation_coefficients = pd.DataFrame(degradation_rows)

    hazard_coefficients = pd.DataFrame(
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

    pit_loss_table = pd.DataFrame(
        [
            {"circuit_id": None, "n_stops": 40, "pit_loss_seconds": 21.0},
            {"circuit_id": "bahrain", "n_stops": 8, "pit_loss_seconds": 22.5},
        ]
    )

    return degradation_coefficients, hazard_coefficients, pit_loss_table


def test_run_produces_deterministic_and_stochastic_results():
    degradation_coefficients, hazard_coefficients, pit_loss_table = _synthetic_coefficients()

    result = comparison.compare_deterministic_vs_stochastic(
        degradation_coefficients,
        hazard_coefficients,
        pit_loss_table,
        circuit_id="bahrain",
        era="2018-2021 aero",
        race_length=20,
        n_scenarios=5,
        seed=11,
    )

    assert result["deterministic"]["status"] in ("optimal", "feasible")
    assert result["stochastic"]["status"] in ("optimal", "feasible")
    assert isinstance(result["deterministic_evaluated_on_scenarios"], float)
    assert isinstance(result["stochastic_evaluated_on_scenarios"], float)
    assert len(result["deterministic_costs"]) == 5
    assert len(result["stochastic_costs"]) == 5


def test_run_evaluates_on_a_different_seed_than_it_optimizes_on(monkeypatch):
    # the stochastic plan is optimized against scenarios sampled with `seed`;
    # if evaluation_scenarios were ever drawn with that same seed instead of
    # `seed + 1`, both plans would be graded on the stochastic plan's own
    # training data and the held-out comparison would silently stop being
    # held out. Spy on sample_scenarios and require at least two distinct
    # seeds across a single run() call so that regression can't slip back in.
    degradation_coefficients, hazard_coefficients, pit_loss_table = _synthetic_coefficients()
    original_sample_scenarios = comparison.scenarios.sample_scenarios
    seen_seeds = []

    def spy(*args, **kwargs):
        seed = kwargs["seed"] if "seed" in kwargs else args[-1]
        seen_seeds.append(seed)
        return original_sample_scenarios(*args, **kwargs)

    monkeypatch.setattr(comparison.scenarios, "sample_scenarios", spy)

    comparison.compare_deterministic_vs_stochastic(
        degradation_coefficients,
        hazard_coefficients,
        pit_loss_table,
        circuit_id="bahrain",
        era="2018-2021 aero",
        race_length=20,
        n_scenarios=5,
        seed=11,
    )

    assert len(seen_seeds) == 2
    assert len(set(seen_seeds)) == 2
