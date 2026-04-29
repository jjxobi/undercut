from __future__ import annotations

import numpy as np
import pandas as pd

# K=5.0 "races worth" of shrinkage. Empirically close to the method-of-moments
# empirical-Bayes optimum for this dataset (~5.7), not an arbitrary choice.
SHRINKAGE_STRENGTH = 5.0

# `mean_position_delta` is close to zero for every circuit by construction --
# Position is a permutation of the classified finishers each race, so gains and
# losses net out within the field. Do not read it as "typical positions gained
# at this circuit"; `position_delta_sd` (the shrinkage-adjusted spread) is the
# statistic this phase actually validates and later phases should use.
#
# This model pools raw CircuitId rather than the layout-variant identifiers
# Phases 1-2 use (see modeling.degradation.circuit_variants) -- a deliberate
# simplification for this phase. Real impact is small (~2.6% on the one known
# case, Bahrain's 2020 Sakhir-layout race folded into the normal Bahrain
# circuit), unlike Phase 1's degradation model where layout conflation caused
# a sign-flipped coefficient. Revisit if a future phase needs circuit-level
# precision this doesn't provide.
RESULT_COLUMNS = ["circuit_id", "n_races", "mean_position_delta", "position_delta_sd"]


def fit_position_volatility(frame: pd.DataFrame) -> pd.DataFrame:
    population_variance = float(frame["PositionDelta"].var())
    population_n_races = frame[["Season", "Round"]].drop_duplicates().shape[0]

    records = [
        {
            "circuit_id": None,
            "n_races": population_n_races,
            "mean_position_delta": float(frame["PositionDelta"].mean()),
            "position_delta_sd": float(np.sqrt(population_variance)),
        }
    ]

    for circuit_id, circuit_frame in frame.groupby("CircuitId"):
        n_races = circuit_frame[["Season", "Round"]].drop_duplicates().shape[0]
        circuit_variance = float(circuit_frame["PositionDelta"].var()) if n_races > 1 else population_variance
        if pd.isna(circuit_variance):
            circuit_variance = population_variance
        shrunk_variance = (
            n_races * circuit_variance + SHRINKAGE_STRENGTH * population_variance
        ) / (n_races + SHRINKAGE_STRENGTH)
        records.append(
            {
                "circuit_id": circuit_id,
                "n_races": n_races,
                "mean_position_delta": float(circuit_frame["PositionDelta"].mean()),
                "position_delta_sd": float(np.sqrt(shrunk_variance)),
            }
        )

    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
