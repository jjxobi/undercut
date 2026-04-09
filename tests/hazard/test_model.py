import numpy as np
import pandas as pd

from modeling.hazard import model


def _synthetic_panel() -> pd.DataFrame:
    # True generative process: -3.7 baseline log-odds, +2.5 on lap one, -0.4 per
    # unit of lap fraction, +0.05 per prior incident this race, plus a per-circuit
    # offset -- "highrisk"/"midrisk" positive, "lowrisk" clearly negative.
    rng = np.random.default_rng(11)
    rows = []
    circuit_effects = {"highrisk": 0.15, "midrisk": 0.0, "lowrisk": -0.15}
    for circuit, effect in circuit_effects.items():
        for _race in range(25):
            race_length = 55
            incidents_so_far = 0
            for lap in range(1, race_length + 1):
                is_lap_one = 1 if lap == 1 else 0
                lap_fraction = lap / race_length
                log_odds = (
                    -3.7 + 2.5 * is_lap_one - 0.4 * lap_fraction
                    + 0.05 * incidents_so_far + effect
                )
                probability = 1 / (1 + np.exp(-log_odds))
                event = rng.random() < probability
                rows.append(
                    {
                        "CircuitId": circuit,
                        "LapFraction": lap_fraction,
                        "IsLapOne": is_lap_one,
                        "IncidentsSoFar": incidents_so_far,
                        "Event": int(event),
                    }
                )
                if event:
                    incidents_so_far += 1
    return pd.DataFrame(rows)


def test_fit_hazard_model_recovers_lap_one_effect():
    panel = _synthetic_panel()

    result = model.fit_hazard_model(panel)

    population_row = result[result["circuit_id"].isna()].iloc[0]
    assert population_row["is_lap_one_coef"] > 1.5


def test_fit_hazard_model_produces_a_row_per_circuit_plus_population():
    panel = _synthetic_panel()

    result = model.fit_hazard_model(panel)

    assert set(result["circuit_id"].dropna()) == {"highrisk", "midrisk", "lowrisk"}
    assert result["circuit_id"].isna().sum() == 1


def test_fit_hazard_model_shrinks_toward_relative_circuit_ordering():
    panel = _synthetic_panel()

    result = model.fit_hazard_model(panel)

    lowrisk = result[result["circuit_id"] == "lowrisk"].iloc[0]["intercept"]
    highrisk = result[result["circuit_id"] == "highrisk"].iloc[0]["intercept"]
    assert lowrisk < highrisk
