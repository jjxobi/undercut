from __future__ import annotations

import pandas as pd

from modeling.optimization import degradation_lookup, pricing, scenarios, strategy

DEFAULT_N_SCENARIOS = 200
DEFAULT_POLICY_SEED = 0


def _priced_cost(
    compounds: list[str],
    stint_lengths: list[int],
    circuit_id: str,
    era: str,
    race_length: int,
    degradation_coefficients: pd.DataFrame,
    real_scenario: list[bool],
    pit_loss_seconds: float,
) -> float:
    tables = [
        degradation_lookup.build_cumulative_cost_table(
            compound, circuit_id, era, race_length, degradation_coefficients
        )
        for compound in compounds
    ]
    return pricing.per_scenario_costs(stint_lengths, tables, [real_scenario], pit_loss_seconds)[0]


def compute_race_benchmarks(
    season: int,
    round_number: int,
    circuit_id: str,
    era: str,
    race_length: int,
    real_scenario: list[bool],
    degradation_coefficients: pd.DataFrame,
    hazard_coefficients: pd.DataFrame,
    pit_loss_seconds: float,
    n_scenarios: int = DEFAULT_N_SCENARIOS,
    policy_seed: int = DEFAULT_POLICY_SEED,
) -> dict:
    oracle_result = strategy.optimize_strategy(
        race_length, circuit_id, era, degradation_coefficients, [real_scenario], pit_loss_seconds
    )
    sampled_scenarios = scenarios.sample_scenarios(
        n_scenarios, race_length, circuit_id, era, hazard_coefficients,
        scenarios.DEFAULT_DURATION_SAMPLES, policy_seed,
    )
    policy_result = strategy.optimize_strategy(
        race_length, circuit_id, era, degradation_coefficients, sampled_scenarios, pit_loss_seconds
    )
    if oracle_result is None or policy_result is None:
        raise ValueError(
            f"no feasible strategy for {season} round {round_number} at race_length={race_length}"
        )

    oracle_cost = _priced_cost(
        oracle_result["compounds"], oracle_result["stint_lengths"], circuit_id, era,
        race_length, degradation_coefficients, real_scenario, pit_loss_seconds,
    )
    policy_cost = _priced_cost(
        policy_result["compounds"], policy_result["stint_lengths"], circuit_id, era,
        race_length, degradation_coefficients, real_scenario, pit_loss_seconds,
    )

    return {
        "oracle_cost_seconds": oracle_cost,
        "oracle_compounds": oracle_result["compounds"],
        "oracle_stint_lengths": oracle_result["stint_lengths"],
        "policy_cost_seconds": policy_cost,
        "policy_compounds": policy_result["compounds"],
        "policy_stint_lengths": policy_result["stint_lengths"],
    }


def price_actual_strategy(
    compounds: list[str],
    stint_lengths: list[int],
    circuit_id: str,
    era: str,
    race_length: int,
    degradation_coefficients: pd.DataFrame,
    real_scenario: list[bool],
    pit_loss_seconds: float,
) -> float:
    return _priced_cost(
        compounds, stint_lengths, circuit_id, era, race_length,
        degradation_coefficients, real_scenario, pit_loss_seconds,
    )
