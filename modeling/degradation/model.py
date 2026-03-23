from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

MIN_LAPS_FOR_CIRCUIT_MODEL = 500
MIN_CIRCUITS_FOR_HIERARCHICAL_FIT = 3

FIT_METHODS = ["lbfgs", "cg", "powell", "bfgs"]
MAX_TAU_TO_BLUP_RATIO = 3.0
BLUP_STD_EPSILON = 0.01

FIXED_FORMULA = "CorrectedLapTimeSeconds ~ TyreLife + TyreLifeSquared + TrackTemp + C(Driver)"
RANDOM_EFFECTS_FORMULA = "~TyreLife"

REQUIRED_COLUMNS = [
    "TyreLife",
    "TyreLifeSquared",
    "TrackTemp",
    "CorrectedLapTimeSeconds",
    "CircuitId",
    "StintKey",
    "Variant",
]

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


def _is_internally_consistent(fit) -> bool:
    tau = float(np.sqrt(fit.cov_re.loc["TyreLife", "TyreLife"]))
    blup_values = [float(v["TyreLife"]) for v in fit.random_effects.values()]
    blup_std = float(np.std(blup_values))
    return tau <= MAX_TAU_TO_BLUP_RATIO * (blup_std + BLUP_STD_EPSILON)


def _fit_mixed_model(mixed_model):
    best_fit = None
    for method in FIT_METHODS:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                candidate = mixed_model.fit(method=[method])
        except Exception:  # noqa: BLE001, S112 - a single solver's numerics must not abort the run
            continue
        if not candidate.converged or not _is_internally_consistent(candidate):
            continue
        if best_fit is None or candidate.llf > best_fit.llf:
            best_fit = candidate
    return best_fit


def _pseudo_r_squared(fit, observed: pd.Series) -> float:
    residual_variance = float(np.var(observed - fit.fittedvalues))
    total_variance = float(np.var(observed))
    if total_variance == 0:
        return 0.0
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
            print(
                f"skip {era} {compound}: insufficient data "
                f"({len(era_compound_frame)} laps, {era_compound_frame['CircuitId'].nunique()} circuits)"
            )
            continue

        mixed_model = smf.mixedlm(
            FIXED_FORMULA,
            data=era_compound_frame,
            groups=era_compound_frame["CircuitId"],
            re_formula=RANDOM_EFFECTS_FORMULA,
            vc_formula={
                "stint": "0 + C(StintKey)",
                "variant": "0 + C(Variant)",
            },
        )
        fit = _fit_mixed_model(mixed_model)
        if fit is None:
            print(f"skip {era} {compound}: no solver converged to a consistent fit")
            continue

        population_coef = float(fit.fe_params["TyreLife"])
        population_squared_coef = float(fit.fe_params["TyreLifeSquared"])
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
            }
        )

        for circuit_id, deviations in fit.random_effects.items():
            circuit_frame = era_compound_frame[era_compound_frame["CircuitId"] == circuit_id]
            effective_coef = population_coef + float(deviations["TyreLife"])
            records.append(
                {
                    "era": era,
                    "compound": compound,
                    "scope": "circuit",
                    "circuit_id": circuit_id,
                    "n_obs": len(circuit_frame),
                    "r_squared": r_squared,
                    "tyre_life_coef": effective_coef,
                    "tyre_life_squared_coef": population_squared_coef,
                    "tyre_life_pvalue": pvalue,
                }
            )

    if not records:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
