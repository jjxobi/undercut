import json

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.main import create_app
from scripts import warm_cache


def _synthetic_data_dir(tmp_path):
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

    rng = np.random.default_rng(7)
    laps_rows = []
    for lap in range(1, 21):
        for driver_index, driver in enumerate(["ver", "ham"]):
            is_pit_lap = driver_index == 0 and lap == 10
            is_out_lap = driver_index == 0 and lap == 11
            lap_time = 90 + rng.normal(0, 0.1)
            if is_pit_lap or is_out_lap:
                lap_time += 20
            laps_rows.append(
                {
                    "Season": 2023,
                    "Round": 1,
                    "Driver": driver,
                    "LapNumber": lap,
                    "LapTime": pd.Timedelta(seconds=lap_time),
                    "TrackStatus": "1",
                    "PitInTime": pd.Timedelta(seconds=(lap - 1) * 90 + 45) if is_pit_lap else pd.NaT,
                    "PitOutTime": pd.NaT,
                    "Time": pd.NaT,
                    "Position": float("nan"),
                }
            )

    # a handful of finished-race finishing times, purely so the position-gap
    # estimator has real same-lap-count adjacent-position gaps to work from --
    # these races aren't in schedule.parquet, so they don't touch pit-loss or
    # strategy solving, only the regret-to-positions conversion
    results_rows = []
    for race_index in range(25):
        season = 2018 + race_index % 5
        round_number = 1 + race_index // 5
        base_time = 4000.0 + rng.normal(0, 5)
        for position, driver in enumerate(["d1", "d2"], start=1):
            gap = rng.uniform(15, 25)
            finish_time = base_time + (position - 1) * gap
            laps_rows.append(
                {
                    "Season": season,
                    "Round": round_number,
                    "Driver": driver,
                    "LapNumber": 20,
                    "LapTime": pd.Timedelta(seconds=90),
                    "TrackStatus": "1",
                    "PitInTime": pd.NaT,
                    "PitOutTime": pd.NaT,
                    "Time": pd.Timedelta(seconds=finish_time),
                    "Position": float(position),
                }
            )
            results_rows.append(
                {
                    "Season": season,
                    "Round": round_number,
                    "Driver": driver,
                    "Code": driver,
                    "Position": position,
                    "Status": "Finished",
                    "GridPosition": position,
                }
            )

    pd.DataFrame(laps_rows).to_parquet(tmp_path / "laps.parquet", index=False)
    pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]}).to_parquet(
        tmp_path / "schedule.parquet", index=False
    )
    pd.DataFrame(results_rows).to_parquet(tmp_path / "results.parquet", index=False)
    return tmp_path


def test_health_check_returns_ok(tmp_path):
    app = create_app(data_dir=_synthetic_data_dir(tmp_path))
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_derives_known_circuits_and_default_race_length(tmp_path):
    data_dir = _synthetic_data_dir(tmp_path)
    app = create_app(data_dir=data_dir)

    with TestClient(app):
        assert app.state.known_circuit_ids == {"bahrain"}
        assert app.state.default_race_lengths["bahrain"] == 20
        assert "2018-2021 aero" in app.state.known_eras
        assert app.state.strategy_cache == {}


def test_startup_loads_a_warm_cache_file_when_present(tmp_path, monkeypatch):
    data_dir = _synthetic_data_dir(tmp_path)

    strategy_key = warm_cache.cache_key("bahrain", "2018-2021 aero", 20, 200, 0)
    warm = {
        "strategy": {
            strategy_key: {
                "status": "optimal",
                "compounds": ["SOFT", "HARD"],
                "stint_lengths": [10, 10],
                "pit_laps": [10],
                "expected_cost_seconds": 12.3,
                "pit_loss_seconds": 22.5,
            }
        },
        "compare": {},
    }
    (data_dir / warm_cache.OUTPUT_FILENAME).write_text(json.dumps(warm))

    app = create_app(data_dir=data_dir)
    with TestClient(app) as client:
        assert app.state.strategy_cache[("bahrain", "2018-2021 aero", 20, 200, 0)].expected_cost_seconds == 12.3

        # a real cache hit must never touch the solver -- prove it by making
        # the solver explode if this request falls through to a live solve
        import modeling.optimization.strategy as strategy_module

        monkeypatch.setattr(
            strategy_module, "optimize_strategy",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("should have been a cache hit")),
        )
        response = client.post(
            "/strategy",
            json={"circuit_id": "bahrain", "era": "2018-2021 aero", "race_length": 20, "n_scenarios": 200, "seed": 0},
        )

    assert response.status_code == 200
    assert response.json()["expected_cost_seconds"] == 12.3
