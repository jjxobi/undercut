from __future__ import annotations

import numpy as np
import pandas as pd

from modeling.hazard import predict as hazard_predict

# Empirical SC/VSC duration distribution derived from real 2018-2026 data
# (median 3 laps, right-skewed 1-9 laps) -- bootstrap-sampled, not a fitted
# parametric distribution.
DEFAULT_DURATION_SAMPLES: list[int] = [
    1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4,
    5, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 8, 8, 9,
]


def sample_scenario(
    race_length: int,
    circuit_id: str,
    era: str,
    hazard_coefficients: pd.DataFrame,
    duration_samples: list[int],
    rng: np.random.Generator,
) -> list[bool]:
    is_active = [False] * (race_length + 1)  # 1-indexed; index 0 unused
    incidents_so_far = 0
    lap = 1
    while lap <= race_length:
        probability = hazard_predict.hazard_probability(
            lap, race_length, incidents_so_far, circuit_id, hazard_coefficients
        )
        if rng.random() < probability:
            duration = int(rng.choice(duration_samples))
            for affected_lap in range(lap, min(lap + duration, race_length + 1)):
                is_active[affected_lap] = True
            incidents_so_far += 1
            lap += duration
        else:
            lap += 1
    return is_active[1:]


def sample_scenarios(
    n_scenarios: int,
    race_length: int,
    circuit_id: str,
    era: str,
    hazard_coefficients: pd.DataFrame,
    duration_samples: list[int],
    seed: int,
) -> list[list[bool]]:
    rng = np.random.default_rng(seed)
    return [
        sample_scenario(race_length, circuit_id, era, hazard_coefficients, duration_samples, rng)
        for _ in range(n_scenarios)
    ]
