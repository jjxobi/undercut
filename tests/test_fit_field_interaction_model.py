import numpy as np
import pandas as pd

from scripts import fit_field_interaction_model


def _synthetic_processed_dir(tmp_path):
    rng = np.random.default_rng(9)
    results_rows, schedule_rows = [], []
    for round_number, (circuit, true_sd) in enumerate(
        [("steady", 1.0), ("chaotic", 8.0)], start=1
    ):
        for race in range(20):
            season, actual_round = 2023, round_number * 100 + race
            schedule_rows.append({"Season": season, "Round": actual_round, "CircuitId": circuit})
            for driver_index in range(20):
                grid = driver_index + 1
                delta = rng.normal(0, true_sd)
                finish = int(np.clip(round(grid - delta), 1, 20))
                results_rows.append(
                    {
                        "Season": season, "Round": actual_round,
                        "Driver": f"driver_{driver_index}",
                        "Position": finish, "Status": "Finished", "GridPosition": grid,
                    }
                )

    results = pd.DataFrame(results_rows)
    schedule = pd.DataFrame(schedule_rows)
    results.to_parquet(tmp_path / "results.parquet", index=False)
    schedule.to_parquet(tmp_path / "schedule.parquet", index=False)
    return tmp_path


def test_run_produces_coefficients_from_processed_parquet(tmp_path):
    processed_dir = _synthetic_processed_dir(tmp_path)

    result = fit_field_interaction_model.run(processed_dir)

    assert set(result["circuit_id"].dropna()) == {"steady", "chaotic"}


def test_main_writes_csv(tmp_path, monkeypatch):
    processed_dir = _synthetic_processed_dir(tmp_path)
    out_path = tmp_path / "field_interaction_coefficients.csv"
    monkeypatch.setattr(
        "sys.argv",
        ["fit_field_interaction_model.py", "--processed-dir", str(processed_dir), "--out", str(out_path)],
    )

    fit_field_interaction_model.main()

    assert out_path.exists()
    written = pd.read_csv(out_path)
    assert len(written) >= 1
