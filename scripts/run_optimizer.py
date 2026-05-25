from __future__ import annotations

import argparse
import statistics
from pathlib import Path

import pandas as pd

from modeling.optimization import degradation_lookup, pit_loss, scenarios, solver, strategy

PROCESSED_DIR = Path("data/processed")
DEFAULT_N_SCENARIOS = 200
GAP_SIGNIFICANCE_MULTIPLIER = 2.0


def _per_scenario_costs(
    stint_lengths: list[int],
    cumulative_cost_tables: list[list[int]],
    evaluation_scenarios: list[list[bool]],
    pit_loss_seconds: float,
) -> list[float]:
    # prices any already-chosen set of stint lengths against each scenario in
    # turn -- solver.solve_stint_lengths would instead re-time the pit stops
    # for whatever scenario set it's handed, which defeats the point of
    # asking how a plan committed to in advance holds up against scenarios
    # it wasn't built around
    pit_laps = []
    running_total = stint_lengths[0]
    for stint_length in stint_lengths[1:]:
        pit_laps.append(running_total)
        running_total += stint_length

    stint_cost_seconds = sum(
        cumulative_cost_tables[i][stint_lengths[i]] / degradation_lookup.CENTISECONDS_PER_SECOND
        for i in range(len(stint_lengths))
    )

    costs = []
    for scenario in evaluation_scenarios:
        pit_cost_seconds = 0.0
        for pit_lap in pit_laps:
            is_sc = scenario[pit_lap - 1]
            pit_cost_seconds += pit_loss_seconds * solver.PIT_LOSS_SC_FRACTION if is_sc else pit_loss_seconds
        costs.append(stint_cost_seconds + pit_cost_seconds)

    return costs


def _expected_cost_of_fixed_plan(
    stint_lengths: list[int],
    cumulative_cost_tables: list[list[int]],
    evaluation_scenarios: list[list[bool]],
    pit_loss_seconds: float,
) -> float:
    costs = _per_scenario_costs(stint_lengths, cumulative_cost_tables, evaluation_scenarios, pit_loss_seconds)
    return statistics.mean(costs)


def run(
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
            f"(every stint needs at least {solver.MIN_STINT_LENGTH} laps) -- try a longer --race-length"
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

    deterministic_costs = _per_scenario_costs(
        deterministic_result["stint_lengths"], deterministic_tables, evaluation_scenarios, pit_loss_seconds
    )
    stochastic_costs = _per_scenario_costs(
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
        "pit_loss_seconds": pit_loss_seconds,
    }


def _positive_int(value: str) -> int:
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError(f"--n-scenarios must be a positive integer, got {value}")
    return n


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a deterministic pit-strategy plan against a stochastic one across sampled safety-car scenarios"
    )
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--circuit-id", type=str, required=True)
    parser.add_argument("--era", type=str, required=True)
    parser.add_argument("--race-length", type=int, required=True)
    parser.add_argument("--n-scenarios", type=_positive_int, default=DEFAULT_N_SCENARIOS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    result = run(
        args.processed_dir, args.circuit_id, args.era, args.race_length, args.n_scenarios, args.seed
    )

    sc_discount_percent = int((1 - solver.PIT_LOSS_SC_FRACTION) * 100)
    print(f"Pit-lane loss estimate: {result['pit_loss_seconds']:.1f}s "
          f"(SC/VSC discount assumed at {sc_discount_percent}%, not estimated from data)")
    print()
    print("DETERMINISTIC plan (optimized assuming no safety car):")
    print(f"  compounds: {result['deterministic']['compounds']}")
    print(f"  stint lengths: {result['deterministic']['stint_lengths']}")
    print(f"  pit laps: {result['deterministic']['pit_laps']}")
    print(f"  expected cost under its own (no-SC) assumption: {result['deterministic']['expected_cost_seconds']:.1f}s")
    print(f"  expected cost on {args.n_scenarios} held-out scenarios: "
          f"{result['deterministic_evaluated_on_scenarios']:.1f}s")
    print()
    print(f"STOCHASTIC plan (optimized across {args.n_scenarios} sampled safety-car scenarios):")
    print(f"  compounds: {result['stochastic']['compounds']}")
    print(f"  stint lengths: {result['stochastic']['stint_lengths']}")
    print(f"  pit laps: {result['stochastic']['pit_laps']}")
    print(f"  expected cost across the scenarios it was optimized on: "
          f"{result['stochastic']['expected_cost_seconds']:.1f}s")
    print(f"  expected cost on {args.n_scenarios} held-out scenarios: "
          f"{result['stochastic_evaluated_on_scenarios']:.1f}s")
    print()
    # both plans are judged here on evaluation_scenarios, a scenario set
    # neither optimization step ever saw -- this is the only comparison
    # that's actually a fair test of whether hedging paid off
    gap = result["deterministic_evaluated_on_scenarios"] - result["stochastic_evaluated_on_scenarios"]
    gap_se = result["gap_standard_error"]
    print(f"On held-out scenarios: deterministic {result['deterministic_evaluated_on_scenarios']:.1f}s vs. "
          f"stochastic {result['stochastic_evaluated_on_scenarios']:.1f}s (gap {gap:+.2f}s ± {gap_se:.2f}s)")
    if abs(gap) <= GAP_SIGNIFICANCE_MULTIPLIER * gap_se:
        print("No meaningful difference between the two plans on held-out scenarios -- "
              "hedging against the safety car neither helped nor hurt here.")
    elif gap > 0:
        print(f"Deterministic plan's confident commitment costs {gap:.1f}s more, on average across "
              f"held-out scenarios, than the plan that hedged against safety-car uncertainty.")
    else:
        print(f"The hedge cost {-gap:.1f}s more, on average across held-out scenarios, than just "
              f"committing to the no-safety-car plan -- hedging wasn't worth it here.")


if __name__ == "__main__":
    main()
