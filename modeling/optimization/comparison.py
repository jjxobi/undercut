from __future__ import annotations

import statistics
from pathlib import Path

import pandas as pd

from modeling.optimization import degradation_lookup, pit_loss, pricing, scenarios, solver, strategy

DEFAULT_N_SCENARIOS = 200
GAP_SIGNIFICANCE_MULTIPLIER = 2.0


def compare_deterministic_vs_stochastic(
    processed_dir: Path,
    circuit_id: str,
    era: str,
    race_length: int,
    n_scenarios: int = DEFAULT_N_SCENARIOS,
    seed: int = 0,
) -> dict:
    degradation_coefficients = pd.read_csv(processed_dir / "degradation_coefficients.csv")
    hazard_coefficients = pd.read_csv(processed_dir / "hazard_coefficients.csv")
    laps = pd.read_parquet(processed_dir / "laps.parquet")
    schedule = pd.read_parquet(processed_dir / "schedule.parquet")

    pit_loss_table = pit_loss.estimate_pit_loss(laps, schedule)
    circuit_pit_loss = pit_loss_table[pit_loss_table["circuit_id"] == circuit_id]
    pit_loss_seconds = (
        float(circuit_pit_loss.iloc[0]["pit_loss_seconds"])
        if len(circuit_pit_loss) > 0
        else float(pit_loss_table[pit_loss_table["circuit_id"].isna()].iloc[0]["pit_loss_seconds"])
    )

    # deterministic: optimize against a single "no safety car" scenario --
    # a confident guess that turns out wrong whenever a real safety car occurs
    deterministic_scenario = [[False] * race_length]
    deterministic_result = strategy.optimize_strategy(
        race_length, circuit_id, era, degradation_coefficients, deterministic_scenario, pit_loss_seconds
    )

    # stochastic: optimize against many sampled realistic safety-car scenarios
    optimization_scenarios = scenarios.sample_scenarios(
        n_scenarios, race_length, circuit_id, era, hazard_coefficients, scenarios.DEFAULT_DURATION_SAMPLES, seed
    )
    stochastic_result = strategy.optimize_strategy(
        race_length, circuit_id, era, degradation_coefficients, optimization_scenarios, pit_loss_seconds
    )

    if deterministic_result is None or stochastic_result is None:
        raise ValueError(
            f"no candidate compound sequence fits a {race_length}-lap race "
            f"(every stint needs at least {solver.MIN_STINT_LENGTH} laps) -- try a longer race length"
        )

    # the stochastic plan was optimized against optimization_scenarios, so
    # scoring either plan there again would just measure how well it fit
    # that particular sample -- draw a second, independent scenario set with
    # a different seed and use it to judge both plans, so the comparison
    # isn't graded on the stochastic plan's own training data
    evaluation_scenarios = scenarios.sample_scenarios(
        n_scenarios, race_length, circuit_id, era, hazard_coefficients, scenarios.DEFAULT_DURATION_SAMPLES, seed + 1
    )

    deterministic_tables = [
        degradation_lookup.build_cumulative_cost_table(
            compound, circuit_id, era, race_length, degradation_coefficients
        )
        for compound in deterministic_result["compounds"]
    ]
    stochastic_tables = [
        degradation_lookup.build_cumulative_cost_table(
            compound, circuit_id, era, race_length, degradation_coefficients
        )
        for compound in stochastic_result["compounds"]
    ]

    deterministic_costs = pricing.per_scenario_costs(
        deterministic_result["stint_lengths"], deterministic_tables, evaluation_scenarios, pit_loss_seconds
    )
    stochastic_costs = pricing.per_scenario_costs(
        stochastic_result["stint_lengths"], stochastic_tables, evaluation_scenarios, pit_loss_seconds
    )
    deterministic_evaluated_cost = statistics.mean(deterministic_costs)
    stochastic_evaluated_cost = statistics.mean(stochastic_costs)

    # the gap between the two plans' means is itself a statistic drawn from a
    # finite scenario sample -- pair the per-scenario costs (same scenario,
    # both plans) and use the standard error of that paired difference so the
    # gap can be judged against its own sampling noise instead of a fixed
    # constant
    paired_differences = [d - s for d, s in zip(deterministic_costs, stochastic_costs)]
    gap_standard_error = (
        statistics.stdev(paired_differences) / len(paired_differences) ** 0.5
        if len(paired_differences) > 1
        else 0.0
    )

    return {
        "deterministic": deterministic_result,
        "stochastic": stochastic_result,
        "deterministic_evaluated_on_scenarios": deterministic_evaluated_cost,
        "stochastic_evaluated_on_scenarios": stochastic_evaluated_cost,
        "gap_standard_error": gap_standard_error,
        "deterministic_costs": deterministic_costs,
        "stochastic_costs": stochastic_costs,
        "pit_loss_seconds": pit_loss_seconds,
    }
