from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from modeling.degradation.predict import degradation_seconds

MIN_LAPS_FOR_CIRCUIT_MODEL = 500
MIN_CIRCUITS_FOR_HIERARCHICAL_FIT = 3
MIN_PLAUSIBILITY_HORIZON = 15
PLAUSIBILITY_STEP = 0.5

FIXED_FORMULA = "CorrectedLapTimeSeconds ~ TyreLife + TyreLifeSquared + TrackTemp + C(Driver)"
RANDOM_EFFECTS_FORMULA = "~TyreLife"

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
    "shrinkage_source",
]


def _plausibility_horizon(tyre_life: pd.Series) -> float:
    return max(MIN_PLAUSIBILITY_HORIZON, round(tyre_life.quantile(0.95)))


def _is_plausible(tyre_life_coef: float, tyre_life_squared_coef: float, horizon: float) -> bool:
    checkpoints = np.arange(1, horizon + PLAUSIBILITY_STEP, PLAUSIBILITY_STEP)
    return all(
        degradation_seconds(t, tyre_life_coef, tyre_life_squared_coef) >= -1e-9 for t in checkpoints
    )


def _pseudo_r_squared(fit, observed: pd.Series) -> float:
    residual_variance = float(np.var(observed - fit.fittedvalues))
    total_variance = float(np.var(observed))
    return 1.0 - residual_variance / total_variance


def fit_degradation_models(
    frame: pd.DataFrame, min_laps_for_circuit_model: int = MIN_LAPS_FOR_CIRCUIT_MODEL
) -> pd.DataFrame:
    complete_frame = frame.dropna(subset=REQUIRED_COLUMNS)
    records = []

    for (era, compound), era_compound_frame in complete_frame.groupby(["RegulationEra", "Compound"]):
        enough_laps = len(era_compound_frame) >= min_laps_for_circuit_model
        enough_circuits = era_compound_frame["CircuitId"].nunique() >= MIN_CIRCUITS_FOR_HIERARCHICAL_FIT
        if not (enough_laps and enough_circuits):
            continue

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mixed_model = smf.mixedlm(
                    FIXED_FORMULA,
                    data=era_compound_frame,
                    groups=era_compound_frame["CircuitId"],
                    re_formula=RANDOM_EFFECTS_FORMULA,
                )
                fit = mixed_model.fit(method=["lbfgs"])
        except Exception:  # noqa: BLE001, S112 - a single group's numerics must not abort the run
            continue
        if not fit.converged:
            continue

        population_coef = float(fit.fe_params["TyreLife"])
        population_squared_coef = float(fit.fe_params["TyreLifeSquared"])
        horizon = _plausibility_horizon(era_compound_frame["TyreLife"])
        if not _is_plausible(population_coef, population_squared_coef, horizon):
            continue

        r_squared = _pseudo_r_squared(fit, era_compound_frame["CorrectedLapTimeSeconds"])
        pvalue = float(fit.pvalues["TyreLife"])

        records.append(
            {
                "era": era,
                "compound": compound,
                "scope": "pooled",
                "circuit_id": None,
                "n_obs": int(fit.nobs),
                "r_squared": r_squared,
                "tyre_life_coef": population_coef,
                "tyre_life_squared_coef": population_squared_coef,
                "tyre_life_pvalue": pvalue,
                "shrinkage_source": None,
            }
        )

        for circuit_id, deviations in fit.random_effects.items():
            circuit_frame = era_compound_frame[era_compound_frame["CircuitId"] == circuit_id]
            effective_coef = population_coef + float(deviations["TyreLife"])
            if _is_plausible(effective_coef, population_squared_coef, horizon):
                tyre_life_coef, source = effective_coef, "circuit_estimate"
            else:
                tyre_life_coef, source = population_coef, "population_fallback"

            records.append(
                {
                    "era": era,
                    "compound": compound,
                    "scope": "circuit",
                    "circuit_id": circuit_id,
                    "n_obs": len(circuit_frame),
                    "r_squared": r_squared,
                    "tyre_life_coef": tyre_life_coef,
                    "tyre_life_squared_coef": population_squared_coef,
                    "tyre_life_pvalue": pvalue,
                    "shrinkage_source": source,
                }
            )

    if not records:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
