import numpy as np
import pandas as pd

from scripts import warm_cache


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


def test_cache_key_round_trips_through_parse():
    key = warm_cache.cache_key("bahrain", "2018-2021 aero", 20, 200, 0)
    assert warm_cache.parse_cache_key(key) == ("bahrain", "2018-2021 aero", 20, 200, 0)


def test_build_warms_the_real_default_combo_for_the_only_circuit_in_the_fixture(tmp_path):
    processed_dir = _synthetic_processed_dir(tmp_path)

    warm = warm_cache.build(processed_dir)

    expected_strategy_key = warm_cache.cache_key(
        "bahrain", "2018-2021 aero", 20, warm_cache.STRATEGY_N_SCENARIOS, warm_cache.SEED
    )
    expected_compare_key = warm_cache.cache_key(
        "bahrain", "2018-2021 aero", 20, warm_cache.COMPARE_N_SCENARIOS, warm_cache.SEED
    )

    assert expected_strategy_key in warm["strategy"]
    assert expected_compare_key in warm["compare"]

    strategy_entry = warm["strategy"][expected_strategy_key]
    assert strategy_entry["status"] in ("optimal", "feasible")
    assert sum(strategy_entry["stint_lengths"]) == 20

    compare_entry = warm["compare"][expected_compare_key]
    assert compare_entry["deterministic"]["status"] in ("optimal", "feasible")
    assert compare_entry["stochastic"]["status"] in ("optimal", "feasible")
    assert isinstance(compare_entry["gap_is_significant"], bool)


def test_write_persists_a_json_file_that_reloads_cleanly(tmp_path):
    processed_dir = _synthetic_processed_dir(tmp_path)
    warm = warm_cache.build(processed_dir)

    out_path = warm_cache.write(warm, processed_dir)

    assert out_path.exists()
    import json

    reloaded = json.loads(out_path.read_text())
    assert reloaded == warm
