import numpy as np
import pandas as pd

from modeling.degradation import model


def _synthetic_frame() -> pd.DataFrame:
    # True generative model: 90s base + 0.08 s/lap tyre degradation (linear) +
    # 0.002 s/lap^2 (mild quadratic) - 0.05 s/lap of fuel burn (RaceLapNumber) +
    # 0.02 s/degree track temp + a 2s driver offset for one driver.
    # bahrain gets enough races to be "credible"; monaco stays sparse and pools.
    rng = np.random.default_rng(42)
    rows = []
    drivers = ["VER", "HAM", "LEC"]
    for circuit, n_races in [("bahrain", 40), ("monaco", 2)]:
        for race in range(n_races):
            for driver in drivers:
                base_temp = 30 + rng.normal(0, 2)
                for lap in range(1, 21):
                    tyre_life = lap
                    race_lap = lap + race
                    temp = base_temp + rng.normal(0, 0.5)
                    noise = rng.normal(0, 0.15)
                    lap_time = (
                        90
                        + 0.08 * tyre_life
                        + 0.002 * tyre_life**2
                        - 0.05 * race_lap
                        + 0.02 * temp
                        + (2.0 if driver == "HAM" else 0.0)
                        + noise
                    )
                    rows.append(
                        {
                            "Compound": "MEDIUM",
                            "CircuitId": circuit,
                            "Driver": driver,
                            "TyreLife": tyre_life,
                            "TyreLifeSquared": tyre_life**2,
                            "RaceLapNumber": race_lap,
                            "TrackTemp": temp,
                            "LapTimeSeconds": lap_time,
                        }
                    )
    return pd.DataFrame(rows)


def test_fit_degradation_models_recovers_true_coefficient_for_credible_circuit():
    frame = _synthetic_frame()

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    bahrain_row = results[(results.scope == "circuit") & (results.circuit_id == "bahrain")].iloc[0]
    assert abs(bahrain_row["tyre_life_coef"] - 0.08) < 0.02
    assert bahrain_row["r_squared"] > 0.8
    assert bahrain_row["tyre_life_pvalue"] < 0.01
    assert bahrain_row["compound"] == "MEDIUM"


def test_fit_degradation_models_pools_sparse_circuit():
    frame = _synthetic_frame()

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    pooled_rows = results[results.scope == "pooled"]
    assert len(pooled_rows) == 1
    assert pooled_rows.iloc[0]["circuit_id"] is None
    circuit_rows = results[results.scope == "circuit"]
    assert list(circuit_rows["circuit_id"]) == ["bahrain"]


def test_fit_degradation_models_handles_multiple_compounds_independently():
    medium = _synthetic_frame()
    soft = medium.copy()
    soft["Compound"] = "SOFT"
    soft["LapTimeSeconds"] = soft["LapTimeSeconds"] - 0.5  # softs are faster
    frame = pd.concat([medium, soft], ignore_index=True)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    assert set(results["compound"]) == {"MEDIUM", "SOFT"}
    assert len(results) == 4  # 2 compounds x (1 circuit-credible + 1 pooled) each
