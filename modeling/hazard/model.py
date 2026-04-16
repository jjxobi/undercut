from __future__ import annotations

import warnings

import pandas as pd
import statsmodels.api as sm

# IncidentsSoFar's coefficient measures as statistically indistinguishable from
# zero on the current dataset (~229 events across ~175 races, mostly 0-1 per
# race -- not enough recurrence to identify a conditional-escalation effect
# yet, if one exists). Kept in the model per the project's stated goal of
# conditioning hazard on incidents so far, and because it's harmless when
# null (near-zero coefficient), but don't read its current value as a
# validated finding -- revisit once more seasons of data accumulate.
FIXED_FORMULA = "Event ~ IsLapOne + LapFraction + IncidentsSoFar"
RANDOM_EFFECTS_FORMULA = {"Variant": "0 + C(Variant)"}

RESULT_COLUMNS = [
    "circuit_id",
    "variant_id",
    "is_latest",
    "intercept",
    "is_lap_one_coef",
    "lap_fraction_coef",
    "incidents_so_far_coef",
]


def fit_hazard_model(panel: pd.DataFrame) -> pd.DataFrame:
    glm_model = sm.BinomialBayesMixedGLM.from_formula(
        FIXED_FORMULA, RANDOM_EFFECTS_FORMULA, panel
    )
    # As of this commit, fit_vb() emits no warnings on real project data -- this
    # block is scoped tightly around just the call so a future convergence issue
    # surfaces instead of being silently swallowed (see Phase 1's degradation
    # model history for why blanket suppression is the wrong default here).
    with warnings.catch_warnings():
        fit = glm_model.fit_vb()

    fixed_effects = dict(zip(fit.model.exog_names, fit.fe_mean))
    variant_to_circuit = panel.groupby("Variant")["CircuitId"].first()
    latest_variant_by_circuit = (
        panel.sort_values(["Season", "Round"]).groupby("CircuitId")["Variant"].last()
    )

    records = [
        {
            "circuit_id": None,
            "variant_id": None,
            "is_latest": False,
            "intercept": fixed_effects["Intercept"],
            "is_lap_one_coef": fixed_effects["IsLapOne"],
            "lap_fraction_coef": fixed_effects["LapFraction"],
            "incidents_so_far_coef": fixed_effects["IncidentsSoFar"],
        }
    ]

    variant_effects = fit.random_effects("Variant")
    for label, row in variant_effects.iterrows():
        variant_id = label.split("[", 1)[1].rstrip("]")
        circuit_id = variant_to_circuit.get(variant_id)
        records.append(
            {
                "circuit_id": circuit_id,
                "variant_id": variant_id,
                "is_latest": bool(latest_variant_by_circuit.get(circuit_id) == variant_id),
                "intercept": fixed_effects["Intercept"] + row["Mean"],
                "is_lap_one_coef": fixed_effects["IsLapOne"],
                "lap_fraction_coef": fixed_effects["LapFraction"],
                "incidents_so_far_coef": fixed_effects["IncidentsSoFar"],
            }
        )

    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
