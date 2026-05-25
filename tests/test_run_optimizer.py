import numpy as np
import pandas as pd
import pytest

from scripts import run_optimizer


def _synthetic_processed_dir(tmp_path):
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
    pd.DataFrame(degradation_rows).to_csv(tmp_path / "degradation_coefficients.csv", index=False)

    hazard_rows = [
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
    pd.DataFrame(hazard_rows).to_csv(tmp_path / "hazard_coefficients.csv", index=False)

    rng = np.random.default_rng(3)
    laps_rows = []
    for lap in range(1, 21):
        for driver_index in range(4):
            is_pit_lap = driver_index == 0 and lap == 10
            is_out_lap = driver_index == 0 and lap == 11
            lap_time = 90 + rng.normal(0, 0.1)
            if is_pit_lap or is_out_lap:
                lap_time += 20
            laps_rows.append(
                {
                    "Season": 2023,
                    "Round": 1,
                    "Driver": f"driver_{driver_index}",
                    "LapNumber": lap,
                    "LapTime": pd.Timedelta(seconds=lap_time),
                    "TrackStatus": "1",
                    "PitInTime": pd.Timedelta(seconds=(lap - 1) * 90 + 45) if is_pit_lap else pd.NaT,
                    "PitOutTime": pd.NaT,
                }
            )
    pd.DataFrame(laps_rows).to_parquet(tmp_path / "laps.parquet", index=False)
    pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]}).to_parquet(
        tmp_path / "schedule.parquet", index=False
    )
    return tmp_path


def test_run_produces_deterministic_and_stochastic_results(tmp_path):
    processed_dir = _synthetic_processed_dir(tmp_path)

    result = run_optimizer.run(
        processed_dir, circuit_id="bahrain", era="2018-2021 aero", race_length=20, n_scenarios=5, seed=11
    )

    assert result["deterministic"]["status"] in ("optimal", "feasible")
    assert result["stochastic"]["status"] in ("optimal", "feasible")
    assert isinstance(result["deterministic_evaluated_on_scenarios"], float)
    assert isinstance(result["stochastic_evaluated_on_scenarios"], float)


def test_run_evaluates_on_a_different_seed_than_it_optimizes_on(tmp_path, monkeypatch):
    # the stochastic plan is optimized against scenarios sampled with `seed`;
    # if evaluation_scenarios were ever drawn with that same seed instead of
    # `seed + 1`, both plans would be graded on the stochastic plan's own
    # training data and the held-out comparison would silently stop being
    # held out. Spy on sample_scenarios and require at least two distinct
    # seeds across a single run() call so that regression can't slip back in.
    processed_dir = _synthetic_processed_dir(tmp_path)
    original_sample_scenarios = run_optimizer.scenarios.sample_scenarios
    seen_seeds = []

    def spy(*args, **kwargs):
        seed = kwargs["seed"] if "seed" in kwargs else args[-1]
        seen_seeds.append(seed)
        return original_sample_scenarios(*args, **kwargs)

    monkeypatch.setattr(run_optimizer.scenarios, "sample_scenarios", spy)

    run_optimizer.run(processed_dir, circuit_id="bahrain", era="2018-2021 aero", race_length=20, n_scenarios=5, seed=11)

    assert len(seen_seeds) == 2
    assert len(set(seen_seeds)) == 2


def test_per_scenario_costs_matches_hand_computation():
    # two one-pit-stop plans over a 10-lap span, pitting after lap 5 (pit_laps
    # derives from stint_lengths, so [5, 5] pits once, after the first stint)
    stint_lengths = [5, 5]
    cumulative_cost_tables = [
        [0, 0, 0, 0, 0, 500],  # first stint: 5 laps cost 500 centiseconds = 5.0s
        [0, 0, 0, 0, 0, 300],  # second stint: 5 laps cost 300 centiseconds = 3.0s
    ]
    pit_loss_seconds = 20.0

    no_sc_scenario = [False] * 10
    sc_scenario = [False] * 10
    sc_scenario[4] = True  # safety car active on lap 5, the pit lap

    costs = run_optimizer._per_scenario_costs(
        stint_lengths, cumulative_cost_tables, [no_sc_scenario, sc_scenario], pit_loss_seconds
    )

    # degradation cost is the same 5.0 + 3.0 = 8.0s either way; the pit lap
    # costs the full 20.0s under green but only 30% of that under a safety car
    assert costs == pytest.approx([8.0 + 20.0, 8.0 + 20.0 * 0.3])


def test_main_runs_without_error(tmp_path, monkeypatch, capsys):
    processed_dir = _synthetic_processed_dir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_optimizer.py",
            "--processed-dir", str(processed_dir),
            "--circuit-id", "bahrain",
            "--era", "2018-2021 aero",
            "--race-length", "20",
            "--n-scenarios", "5",
            "--seed", "11",
        ],
    )

    run_optimizer.main()

    captured = capsys.readouterr()
    assert "deterministic" in captured.out.lower()
    assert "stochastic" in captured.out.lower()
