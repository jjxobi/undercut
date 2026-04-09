from __future__ import annotations

import warnings

import pandas as pd
import statsmodels.api as sm

FIXED_FORMULA = "Event ~ IsLapOne + LapFraction + IncidentsSoFar"
RANDOM_EFFECTS_FORMULA = {"CircuitId": "0 + C(CircuitId)"}

RESULT_COLUMNS = [
    "circuit_id",
    "intercept",
    "is_lap_one_coef",
    "lap_fraction_coef",
    "incidents_so_far_coef",
]


def fit_hazard_model(panel: pd.DataFrame) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        glm_model = sm.BinomialBayesMixedGLM.from_formula(
            FIXED_FORMULA, RANDOM_EFFECTS_FORMULA, panel
        )
        fit = glm_model.fit_vb()

    fixed_effects = dict(zip(fit.model.exog_names, fit.fe_mean))

    records = [
        {
            "circuit_id": None,
            "intercept": fixed_effects["Intercept"],
            "is_lap_one_coef": fixed_effects["IsLapOne"],
            "lap_fraction_coef": fixed_effects["LapFraction"],
            "incidents_so_far_coef": fixed_effects["IncidentsSoFar"],
        }
    ]

    circuit_effects = fit.random_effects("CircuitId")
    for label, row in circuit_effects.iterrows():
        circuit_id = label.split("[", 1)[1].rstrip("]")
        records.append(
            {
                "circuit_id": circuit_id,
                "intercept": fixed_effects["Intercept"] + row["Mean"],
                "is_lap_one_coef": fixed_effects["IsLapOne"],
                "lap_fraction_coef": fixed_effects["LapFraction"],
                "incidents_so_far_coef": fixed_effects["IncidentsSoFar"],
            }
        )

    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
