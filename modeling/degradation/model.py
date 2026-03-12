from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf

MIN_LAPS_FOR_CIRCUIT_MODEL = 300

POOLED_FORMULA = "LapTimeSeconds ~ TyreLife + TyreLifeSquared + RaceLapNumber + TrackTemp + C(CircuitId) + C(Driver)"
CIRCUIT_FORMULA = "LapTimeSeconds ~ TyreLife + TyreLifeSquared + RaceLapNumber + TrackTemp + C(Driver)"

RESULT_COLUMNS = [
    "compound",
    "scope",
    "circuit_id",
    "n_obs",
    "r_squared",
    "tyre_life_coef",
    "tyre_life_squared_coef",
    "tyre_life_pvalue",
]


def _fit_result(model_fit, scope: str, circuit_id: str | None) -> dict:
    return {
        "scope": scope,
        "circuit_id": circuit_id,
        "n_obs": int(model_fit.nobs),
        "r_squared": float(model_fit.rsquared),
        "tyre_life_coef": float(model_fit.params.get("TyreLife", 0.0)),
        "tyre_life_squared_coef": float(model_fit.params.get("TyreLifeSquared", 0.0)),
        "tyre_life_pvalue": float(model_fit.pvalues.get("TyreLife", 1.0)),
    }


def fit_degradation_models(
    frame: pd.DataFrame, min_laps_for_circuit_model: int = MIN_LAPS_FOR_CIRCUIT_MODEL
) -> pd.DataFrame:
    records = []
    for compound, compound_frame in frame.groupby("Compound"):
        circuit_counts = compound_frame["CircuitId"].value_counts()
        credible_circuits = circuit_counts[circuit_counts >= min_laps_for_circuit_model].index.tolist()
        sparse_frame = compound_frame[~compound_frame["CircuitId"].isin(credible_circuits)]

        # Only fit a pooled model when there's at least as much data as the
        # circuit-credibility bar requires. Below that, statsmodels can still
        # "succeed" on a rank-deficient design (e.g. many circuits with a
        # handful of laps each) by falling back to a pseudo-inverse, which
        # silently produces a perfect-looking but meaningless fit.
        if len(sparse_frame) >= min_laps_for_circuit_model:
            fit = smf.ols(POOLED_FORMULA, data=sparse_frame).fit()
            result = _fit_result(fit, "pooled", None)
            result["compound"] = compound
            records.append(result)

        for circuit_id in credible_circuits:
            circuit_frame = compound_frame[compound_frame["CircuitId"] == circuit_id]
            fit = smf.ols(CIRCUIT_FORMULA, data=circuit_frame).fit()
            result = _fit_result(fit, "circuit", circuit_id)
            result["compound"] = compound
            records.append(result)

    if not records:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
