import numpy as np
import pandas as pd

from scripts import run_evaluation


def _synthetic_processed_dir(tmp_path):
    degradation_rows = []
    for compound, coef in [("SOFT", 0.20), ("MEDIUM", 0.10), ("HARD", 0.05)]:
        degradation_rows.append(
            {
                "era": "2022-2025 ground-effect",
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

    rng = np.random.default_rng(5)
    laps_rows = []
    for lap in range(1, 21):
        for driver_index, driver in enumerate(["ver", "ham"]):
            is_pit_lap = driver_index == 0 and lap == 10
            is_out_lap = driver_index == 0 and lap == 11
            track_status = "4" if lap == 9 else "1"
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
                    "TrackStatus": track_status,
                    "PitInTime": pd.Timedelta(seconds=(lap - 1) * 90 + 45) if is_pit_lap else pd.NaT,
                    "PitOutTime": pd.NaT,
                    "Time": pd.Timedelta(seconds=lap * 90),
                    "Position": float(driver_index + 1),
                }
            )
    pd.DataFrame(laps_rows).to_parquet(tmp_path / "laps.parquet", index=False)

    pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]}).to_parquet(
        tmp_path / "schedule.parquet", index=False
    )

    pd.DataFrame(
        [
            {"Season": 2023, "Round": 1, "Driver": "ver", "Stint": 1.0, "Compound": "SOFT", "StintLength": 10.0},
            {"Season": 2023, "Round": 1, "Driver": "ver", "Stint": 2.0, "Compound": "MEDIUM", "StintLength": 10.0},
        ]
    ).to_parquet(tmp_path / "stints.parquet", index=False)

    pd.DataFrame(
        [
            {"Season": 2023, "Round": 1, "Code": "ver", "Status": "Finished"},
            {"Season": 2023, "Round": 1, "Code": "ham", "Status": "Finished"},
        ]
    ).to_parquet(tmp_path / "results.parquet", index=False)

    return tmp_path


def test_run_produces_one_row_per_qualifying_driver_race(tmp_path):
    processed_dir = _synthetic_processed_dir(tmp_path)

    report = run_evaluation.run(processed_dir, n_scenarios=5, policy_seed=1)

    assert list(report.columns) == run_evaluation.REPORT_COLUMNS
    assert len(report) == 1
    row = report.iloc[0]
    assert row["driver"] == "ver"
    assert row["actual_regret_seconds"] >= 0
    assert row["policy_regret_seconds"] >= 0


def test_main_writes_csv_and_prints_headline(tmp_path, monkeypatch, capsys):
    processed_dir = _synthetic_processed_dir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["run_evaluation.py", "--processed-dir", str(processed_dir), "--n-scenarios", "5", "--seed", "1"],
    )

    run_evaluation.main()

    assert (processed_dir / "regret_report.csv").exists()
    captured = capsys.readouterr()
    assert "regret" in captured.out.lower()
