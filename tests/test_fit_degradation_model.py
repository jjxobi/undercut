import numpy as np
import pandas as pd

from scripts import fit_degradation_model

DRIVERS = ["VER", "HAM", "LEC", "RUS", "SAI", "NOR", "ALO", "PER"]  # 8 -- clears
# circuit_variants.MIN_DRIVERS_FOR_SIGNATURE so a real (single) variant gets
# detected per circuit, rather than every race being dropped from the
# signature computation and every lap ending up with a null Variant (which
# would then get dropped entirely by fit_degradation_models' REQUIRED_COLUMNS
# dropna and silently zero out the whole test).
SECTOR_FRACTIONS = (0.30, 0.35, 0.35)


def _synthetic_processed_dir(tmp_path):
    # Two stints per race/driver (a pit stop after lap 7) so TyreLife resets to 1
    # while LapNumber keeps climbing -- without this, TyreLife and RaceLapNumber
    # are perfectly collinear (both just count up from 1) and the regression
    # cannot separate the tyre-degradation effect from the fuel-burn effect.
    # This mirrors why real data supports the separation: different stint
    # strategies decouple the two. Verified against this exact fixture before
    # being written here -- do not simplify back to one stint per race.
    rng = np.random.default_rng(7)
    rows = []
    for race in range(30):
        for driver in DRIVERS:
            race_lap = 0
            # stint_number tracks which of the two stint-length loops we're in
            # directly, rather than comparing tyre_life to stint_length (which
            # is always true within tyre_life's own range and previously made
            # every lap's Stint come out 1 -- a no-op that gave StintKey zero
            # real variation).
            for stint_number, stint_length in enumerate((7, 8), start=1):
                for tyre_life in range(1, stint_length + 1):
                    race_lap += 1
                    is_accurate = tyre_life != 1  # fresh-tyre out-lap flagged inaccurate
                    lap_time = (
                        92 + 0.09 * tyre_life + 0.001 * tyre_life**2 - 0.04 * race_lap
                        + rng.normal(0, 0.1)
                    )
                    s1 = lap_time * SECTOR_FRACTIONS[0] + rng.normal(0, 0.02)
                    s2 = lap_time * SECTOR_FRACTIONS[1] + rng.normal(0, 0.02)
                    s3 = lap_time - s1 - s2
                    rows.append(
                        {
                            "Season": 2023,
                            "Round": 1,
                            "Driver": driver,
                            "LapNumber": race_lap,
                            "Stint": stint_number,
                            "Compound": "MEDIUM",
                            "TyreLife": float(tyre_life),
                            "Time": pd.Timedelta(minutes=race * 90 + race_lap),
                            "LapTime": pd.Timedelta(seconds=lap_time),
                            "Sector1Time": pd.Timedelta(seconds=s1),
                            "Sector2Time": pd.Timedelta(seconds=s2),
                            "Sector3Time": pd.Timedelta(seconds=s3),
                            "IsAccurate": is_accurate,
                            "TrackStatus": "1",
                            "PitInTime": pd.NaT,
                            "PitOutTime": pd.NaT,
                        }
                    )
    laps = pd.DataFrame(rows)
    # give each synthetic "race" its own Round so accurate_laps + grouping behave like real data
    laps["Round"] = (laps.index // (len(DRIVERS) * 15)) + 1

    # Spread rounds across 3 circuits (not just one) -- the hierarchical fit
    # needs several distinct circuits to estimate a random-effects variance
    # component at all; a single-circuit fixture can no longer produce any
    # output under this fitting method.
    circuit_ids = ["bahrain", "jeddah", "melbourne"]
    schedule = pd.DataFrame(
        {
            "Season": [2023] * 30,
            "Round": range(1, 31),
            "CircuitId": [circuit_ids[r % 3] for r in range(30)],
        }
    )
    # TrackTemp varies race to race (not a constant) -- a constant covariate is
    # perfectly collinear with the intercept once every circuit's data shares
    # the exact same value, which makes the hierarchical fit's design matrix
    # singular.
    weather = pd.DataFrame(
        {
            "Season": [2023] * 30,
            "Round": range(1, 31),
            "Time": [pd.Timedelta(minutes=r * 90) for r in range(30)],
            "TrackTemp": [32.0 + rng.normal(0, 2) for _ in range(30)],
            "AirTemp": [24.0] * 30,
            "Rainfall": [False] * 30,
        }
    )

    laps.to_parquet(tmp_path / "laps.parquet", index=False)
    schedule.to_parquet(tmp_path / "schedule.parquet", index=False)
    weather.to_parquet(tmp_path / "weather.parquet", index=False)
    return tmp_path


def test_synthetic_fixture_actually_has_two_distinct_stints_per_driver_race(tmp_path):
    # Guards against the fixture silently degrading back into a no-op: the
    # whole point of two stints per driver-race is to give the stint-level
    # variance component (features.add_stint_key's StintKey) more than one
    # value to distinguish, per driver-race. Without this, the fixture
    # provides zero real coverage of that mechanism while still "looking"
    # correct at a glance.
    processed_dir = _synthetic_processed_dir(tmp_path)
    laps = pd.read_parquet(processed_dir / "laps.parquet")

    assert set(laps["Stint"].unique()) == {1, 2}
    stint_keys_per_driver_race = laps.groupby(["Season", "Round", "Driver"])["Stint"].nunique()
    assert (stint_keys_per_driver_race == 2).all()


def test_run_produces_coefficients_from_processed_parquet(tmp_path):
    processed_dir = _synthetic_processed_dir(tmp_path)

    result = fit_degradation_model.run(processed_dir, min_laps_for_circuit_model=5)

    assert len(result) >= 1
    assert "MEDIUM" in set(result["compound"])
    assert (result["tyre_life_coef"] > 0).all()


def test_main_writes_csv(tmp_path, monkeypatch, capsys):
    processed_dir = _synthetic_processed_dir(tmp_path)
    out_path = tmp_path / "degradation_coefficients.csv"
    monkeypatch.setattr(
        "sys.argv",
        ["fit_degradation_model.py", "--processed-dir", str(processed_dir), "--out", str(out_path), "--min-laps", "5"],
    )

    fit_degradation_model.main()

    assert out_path.exists()
    written = pd.read_csv(out_path)
    assert len(written) >= 1
