from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modeling.optimization import degradation_lookup, pit_loss, scenarios, solver, strategy

PROCESSED_DIR = Path("data/processed")
DEFAULT_N_SCENARIOS = 200


def _expected_cost_of_fixed_plan(
    stint_lengths: list[int],
    cumulative_cost_tables: list[list[int]],
    sampled_scenarios: list[list[bool]],
    pit_loss_seconds: float,
) -> float:
    # prices a plan's own already-chosen stint lengths against the sampled
    # scenarios -- solver.solve_stint_lengths would instead re-time the pit
    # stops for whatever scenario set it's handed, which defeats the point
    # of asking how a plan committed to in advance holds up later
    pit_laps = []
    running_total = stint_lengths[0]
    for stint_length in stint_lengths[1:]:
        pit_laps.append(running_total)
        running_total += stint_length

    stint_cost_seconds = sum(
        cumulative_cost_tables[i][stint_lengths[i]] / degradation_lookup.CENTISECONDS_PER_SECOND
        for i in range(len(stint_lengths))
    )

    total_cost_seconds = 0.0
    for scenario in sampled_scenarios:
        pit_cost_seconds = 0.0
        for pit_lap in pit_laps:
            is_sc = scenario[pit_lap - 1]
            pit_cost_seconds += pit_loss_seconds * solver.PIT_LOSS_SC_FRACTION if is_sc else pit_loss_seconds
        total_cost_seconds += stint_cost_seconds + pit_cost_seconds

    return total_cost_seconds / len(sampled_scenarios)


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
    sampled_scenarios = scenarios.sample_scenarios(
        n_scenarios, race_length, circuit_id, era, hazard_coefficients, scenarios.DEFAULT_DURATION_SAMPLES, seed
    )
    stochastic_result = strategy.optimize_strategy(
        race_length, circuit_id, era, degradation_coefficients, sampled_scenarios, pit_loss_seconds
    )

    # the failure demonstration: price the DETERMINISTIC plan's own already
    # chosen stint lengths against the realistic scenario set, to see how
    # much worse its confident commitment performs once safety cars are real
    deterministic_tables = [
        degradation_lookup.build_cumulative_cost_table(
            compound, circuit_id, era, race_length, degradation_coefficients
        )
        for compound in deterministic_result["compounds"]
    ]
    deterministic_evaluated_cost = _expected_cost_of_fixed_plan(
        deterministic_result["stint_lengths"], deterministic_tables, sampled_scenarios, pit_loss_seconds
    )

    return {
        "deterministic": deterministic_result,
        "stochastic": stochastic_result,
        "deterministic_evaluated_on_scenarios": deterministic_evaluated_cost,
        "pit_loss_seconds": pit_loss_seconds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a deterministic pit-strategy plan against a stochastic one across sampled safety-car scenarios"
    )
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--circuit-id", type=str, required=True)
    parser.add_argument("--era", type=str, required=True)
    parser.add_argument("--race-length", type=int, required=True)
    parser.add_argument("--n-scenarios", type=int, default=DEFAULT_N_SCENARIOS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    result = run(
        args.processed_dir, args.circuit_id, args.era, args.race_length, args.n_scenarios, args.seed
    )

    sc_discount_percent = int((1 - solver.PIT_LOSS_SC_FRACTION) * 100)
    print(f"Pit-lane loss estimate: {result['pit_loss_seconds']:.1f}s "
          f"(SC/VSC discount assumed at {sc_discount_percent}% -- not derived from data, see plan notes)")
    print()
    print("DETERMINISTIC plan (optimized assuming no safety car):")
    print(f"  compounds: {result['deterministic']['compounds']}")
    print(f"  stint lengths: {result['deterministic']['stint_lengths']}")
    print(f"  pit laps: {result['deterministic']['pit_laps']}")
    print(f"  expected cost under its own (no-SC) assumption: {result['deterministic']['expected_cost_seconds']:.1f}s")
    print(f"  expected cost when re-evaluated against {args.n_scenarios} realistic scenarios: "
          f"{result['deterministic_evaluated_on_scenarios']:.1f}s")
    print()
    print(f"STOCHASTIC plan (optimized across {args.n_scenarios} sampled safety-car scenarios):")
    print(f"  compounds: {result['stochastic']['compounds']}")
    print(f"  stint lengths: {result['stochastic']['stint_lengths']}")
    print(f"  pit laps: {result['stochastic']['pit_laps']}")
    print(f"  expected cost across the same {args.n_scenarios} scenarios: "
          f"{result['stochastic']['expected_cost_seconds']:.1f}s")
    print()
    gap = result["deterministic_evaluated_on_scenarios"] - result["stochastic"]["expected_cost_seconds"]
    print(f"Deterministic plan's confident commitment costs {gap:.1f}s more, on average across "
          f"realistic scenarios, than the plan that hedged against safety-car uncertainty.")


if __name__ == "__main__":
    main()
