import numpy as np
import pandas as pd

from scripts import fit_hazard_model


def _synthetic_processed_dir(tmp_path):
    rng = np.random.default_rng(3)
    laps_rows, status_rows, schedule_rows = [], [], []
    circuits = ["circuita", "circuitb", "circuitc"]
    for round_number, circuit in enumerate(circuits, start=1):
        for race in range(15):
            season, actual_round = 2023, round_number * 100 + race
            schedule_rows.append({"Season": season, "Round": actual_round, "CircuitId": circuit})
            race_length = 40
            for lap in range(1, race_length + 1):
                lap_start = pd.Timedelta(seconds=(lap - 1) * 90)
                laps_rows.append(
                    {
                        "Season": season, "Round": actual_round,
                        "LapNumber": lap, "LapStartTime": lap_start,
                    }
                )
            # roughly one hazard event per race, timed within the race at random
            if rng.random() < 0.6:
                event_lap = rng.integers(1, race_length + 1)
                event_time = pd.Timedelta(seconds=(event_lap - 1) * 90 + 10)
                status_rows.append(
                    {"Season": season, "Round": actual_round, "Time": event_time, "Status": "4"}
                )
            status_rows.append(
                {"Season": season, "Round": actual_round, "Time": pd.Timedelta(seconds=0), "Status": "1"}
            )

    laps = pd.DataFrame(laps_rows)
    track_status = pd.DataFrame(status_rows)
    schedule = pd.DataFrame(schedule_rows)

    laps.to_parquet(tmp_path / "laps.parquet", index=False)
    track_status.to_parquet(tmp_path / "track_status.parquet", index=False)
    schedule.to_parquet(tmp_path / "schedule.parquet", index=False)
    return tmp_path


def test_run_produces_coefficients_from_processed_parquet(tmp_path):
    processed_dir = _synthetic_processed_dir(tmp_path)

    result = fit_hazard_model.run(processed_dir)

    assert len(result) >= 1
    assert result["circuit_id"].isna().sum() == 1


def test_main_writes_csv(tmp_path, monkeypatch):
    processed_dir = _synthetic_processed_dir(tmp_path)
    out_path = tmp_path / "hazard_coefficients.csv"
    monkeypatch.setattr(
        "sys.argv",
        ["fit_hazard_model.py", "--processed-dir", str(processed_dir), "--out", str(out_path)],
    )

    fit_hazard_model.main()

    assert out_path.exists()
    written = pd.read_csv(out_path)
    assert len(written) >= 1
