from __future__ import annotations

from itertools import pairwise

import pandas as pd
import statsmodels.formula.api as smf

from modeling.degradation.predict import degradation_seconds

MIN_LAPS_FOR_CIRCUIT_MODEL = 300
MAX_TYRE_LIFE_FOR_PLAUSIBILITY_CHECK = 30

POOLED_FORMULA = "CorrectedLapTimeSeconds ~ TyreLife + TyreLifeSquared + TrackTemp + C(CircuitId) + C(Driver)"
CIRCUIT_FORMULA = "CorrectedLapTimeSeconds ~ TyreLife + TyreLifeSquared + TrackTemp + C(Driver)"

REQUIRED_COLUMNS = ["TyreLife", "TyreLifeSquared", "TrackTemp", "CorrectedLapTimeSeconds", "CircuitId"]

RESULT_COLUMNS = [
    "era",
    "compound",
    "scope",
    "circuit_id",
    "n_obs",
    "r_squared",
    "tyre_life_coef",
    "tyre_life_squared_coef",
    "tyre_life_pvalue",
]


def _is_plausible(tyre_life_coef: float, tyre_life_squared_coef: float) -> bool:
    curve = [
        degradation_seconds(t, tyre_life_coef, tyre_life_squared_coef)
        for t in range(1, MAX_TYRE_LIFE_FOR_PLAUSIBILITY_CHECK + 1)
    ]
    monotone_non_decreasing = all(later >= earlier - 1e-9 for earlier, later in pairwise(curve))
    return monotone_non_decreasing and curve[-1] > 0


def _fit_result(model_fit, era: str, compound: str, scope: str, circuit_id: str | None) -> dict:
    return {
        "era": era,
        "compound": compound,
        "scope": scope,
        "circuit_id": circuit_id,
        "n_obs": int(model_fit.nobs),
        "r_squared": float(model_fit.rsquared),
        "tyre_life_coef": float(model_fit.params["TyreLife"]),
        "tyre_life_squared_coef": float(model_fit.params["TyreLifeSquared"]),
        "tyre_life_pvalue": float(model_fit.pvalues["TyreLife"]),
    }


def fit_degradation_models(
    frame: pd.DataFrame, min_laps_for_circuit_model: int = MIN_LAPS_FOR_CIRCUIT_MODEL
) -> pd.DataFrame:
    records = []
    complete_frame = frame.dropna(subset=REQUIRED_COLUMNS)

    for (era, compound), era_compound_frame in complete_frame.groupby(["RegulationEra", "Compound"]):
        circuit_counts = era_compound_frame["CircuitId"].value_counts()
        credible_circuits = circuit_counts[circuit_counts >= min_laps_for_circuit_model].index.tolist()

        rejected_frames = [era_compound_frame[~era_compound_frame["CircuitId"].isin(credible_circuits)]]
        for circuit_id in credible_circuits:
            circuit_frame = era_compound_frame[era_compound_frame["CircuitId"] == circuit_id]
            fit = smf.ols(CIRCUIT_FORMULA, data=circuit_frame).fit()
            if _is_plausible(fit.params["TyreLife"], fit.params["TyreLifeSquared"]):
                records.append(_fit_result(fit, era, compound, "circuit", circuit_id))
            else:
                rejected_frames.append(circuit_frame)

        pooled_candidates = pd.concat(rejected_frames, ignore_index=True)
        if len(pooled_candidates) >= min_laps_for_circuit_model:
            fit = smf.ols(POOLED_FORMULA, data=pooled_candidates).fit()
            if _is_plausible(fit.params["TyreLife"], fit.params["TyreLifeSquared"]):
                records.append(_fit_result(fit, era, compound, "pooled", None))

    if not records:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
