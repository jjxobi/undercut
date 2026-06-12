from __future__ import annotations

import argparse
from pathlib import Path

from modeling.optimization import comparison, solver

PROCESSED_DIR = Path("data/processed")


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
    parser.add_argument("--n-scenarios", type=_positive_int, default=comparison.DEFAULT_N_SCENARIOS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    result = comparison.compare_deterministic_vs_stochastic(
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
    if abs(gap) <= comparison.GAP_SIGNIFICANCE_MULTIPLIER * gap_se:
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
