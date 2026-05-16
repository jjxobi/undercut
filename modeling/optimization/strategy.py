from __future__ import annotations

import pandas as pd

from modeling.optimization import degradation_lookup, solver

CANDIDATE_COMPOUND_SEQUENCES: list[list[str]] = [
    ["MEDIUM", "HARD"],
    ["SOFT", "HARD"],
    ["SOFT", "MEDIUM"],
    ["SOFT", "MEDIUM", "HARD"],
    ["MEDIUM", "HARD", "MEDIUM"],
]


def optimize_strategy(
    race_length: int,
    circuit_id: str,
    era: str,
    degradation_coefficients: pd.DataFrame,
    scenarios: list[list[bool]],
    pit_loss_seconds: float,
    compound_sequences: list[list[str]] = CANDIDATE_COMPOUND_SEQUENCES,
) -> dict:
    best = None
    for sequence in compound_sequences:
        tables = [
            degradation_lookup.build_cumulative_cost_table(
                compound, circuit_id, era, race_length, degradation_coefficients
            )
            for compound in sequence
        ]
        result = solver.solve_stint_lengths(race_length, tables, scenarios, pit_loss_seconds)
        if result["status"] == "infeasible":
            continue
        result["compounds"] = sequence
        if best is None or result["expected_cost_seconds"] < best["expected_cost_seconds"]:
            best = result
    return best
