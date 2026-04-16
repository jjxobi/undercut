import numpy as np
import pandas as pd

from scripts import fit_hazard_model

N_DRIVERS = 8  # matches circuit_variants.MIN_DRIVERS_FOR_SIGNATURE


def _synthetic_processed_dir(tmp_path):
    rng = np.random.default_rng(3)
    laps_rows, status_rows, schedule_rows = [], [], []
    # sector fractions differ per circuit but are constant across a circuit's
    # races, so variant detection assigns exactly one variant per circuit --
    # this test is about the orchestration wiring, not layout-splitting itself
    # (that's covered by modeling/degradation's own circuit_variants tests).
    circuits = {
        "circuita": (0.30, 0.35, 0.35),
        "circuitb": (0.25, 0.40, 0.35),
        "circuitc": (0.33, 0.33, 0.34),
    }
    for round_number, (circuit, sector_fracs) in enumerate(circuits.items(), start=1):
        for race in range(15):
            season, actual_round = 2023, round_number * 100 + race
            schedule_rows.append({"Season": season, "Round": actual_round, "CircuitId": circuit})
            race_length = 40
            for lap in range(1, race_length + 1):
                lap_start = pd.Timedelta(seconds=(lap - 1) * 90)
                for driver_index in range(N_DRIVERS):
                    total = 90.0 + rng.normal(0, 0.3)
                    s1 = total * sector_fracs[0] + rng.normal(0, 0.03)
                    s2 = total * sector_fracs[1] + rng.normal(0, 0.03)
                    s3 = total - s1 - s2
                    laps_rows.append(
                        {
                            "Season": season, "Round": actual_round,
                            "LapNumber": lap, "LapStartTime": lap_start,
                            "Driver": f"D{driver_index}",
                            "Sector1Time": pd.Timedelta(seconds=s1),
                            "Sector2Time": pd.Timedelta(seconds=s2),
                            "Sector3Time": pd.Timedelta(seconds=s3),
                            "LapTime": pd.Timedelta(seconds=s1 + s2 + s3),
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
