from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modeling import config
from modeling.evaluation import actual_strategy, position_gap, real_scenario, regret
from modeling.optimization import pit_loss

PROCESSED_DIR = Path("data/processed")
REPORT_FILENAME = "regret_report.csv"
REPORT_COLUMNS = [
    "season", "round", "driver", "circuit_id", "era", "race_length",
    "actual_cost_seconds", "policy_cost_seconds", "oracle_cost_seconds",
    "actual_regret_seconds", "policy_regret_seconds",
]


def run(
    processed_dir: Path,
    n_scenarios: int = regret.DEFAULT_N_SCENARIOS,
    policy_seed: int = regret.DEFAULT_POLICY_SEED,
) -> pd.DataFrame:
    degradation_coefficients = pd.read_csv(processed_dir / "degradation_coefficients.csv")
    hazard_coefficients = pd.read_csv(processed_dir / "hazard_coefficients.csv")
    laps = pd.read_parquet(processed_dir / "laps.parquet")
    schedule = pd.read_parquet(processed_dir / "schedule.parquet")
    stints = pd.read_parquet(processed_dir / "stints.parquet")
    results = pd.read_parquet(processed_dir / "results.parquet")

    race_lengths = laps.groupby(["Season", "Round"])["LapNumber"].max()
    circuit_by_race = schedule.set_index(["Season", "Round"])["CircuitId"]
    pit_loss_table = pit_loss.estimate_pit_loss(laps, schedule)

    strategies = actual_strategy.extract_actual_strategies(stints, results, race_lengths)

    rows = []
    for (season, round_number), race_strategies in strategies.groupby(["season", "round"]):
        if (season, round_number) not in circuit_by_race.index:
            print(f"skip {season} round {round_number}: not in schedule")
            continue
        circuit_id = circuit_by_race.loc[(season, round_number)]
        era = config.regulation_era(season)
        race_length = int(race_lengths.loc[(season, round_number)])

        circuit_pit_loss = pit_loss_table[pit_loss_table["circuit_id"] == circuit_id]
        pit_loss_seconds = (
            float(circuit_pit_loss.iloc[0]["pit_loss_seconds"])
            if len(circuit_pit_loss) > 0
            else float(pit_loss_table[pit_loss_table["circuit_id"].isna()].iloc[0]["pit_loss_seconds"])
        )

        try:
            scenario = real_scenario.build_real_scenario(laps, season, round_number, race_length)
            benchmarks = regret.compute_race_benchmarks(
                season, round_number, circuit_id, era, race_length, scenario,
                degradation_coefficients, hazard_coefficients, pit_loss_seconds,
                n_scenarios=n_scenarios, policy_seed=policy_seed,
            )
        except Exception as exc:  # noqa: BLE001 - one bad race must not abort the run
            print(f"skip {season} round {round_number}: {exc}")
            continue

        for _, driver_row in race_strategies.iterrows():
            actual_cost = regret.price_actual_strategy(
                driver_row["compounds"], driver_row["stint_lengths"], circuit_id, era,
                race_length, degradation_coefficients, scenario, pit_loss_seconds,
            )
            rows.append(
                {
                    "season": season,
                    "round": round_number,
                    "driver": driver_row["driver"],
                    "circuit_id": circuit_id,
                    "era": era,
                    "race_length": race_length,
                    "actual_cost_seconds": actual_cost,
                    "policy_cost_seconds": benchmarks["policy_cost_seconds"],
                    "oracle_cost_seconds": benchmarks["oracle_cost_seconds"],
                    "actual_regret_seconds": actual_cost - benchmarks["oracle_cost_seconds"],
                    "policy_regret_seconds": benchmarks["policy_cost_seconds"] - benchmarks["oracle_cost_seconds"],
                }
            )

    return pd.DataFrame.from_records(rows, columns=REPORT_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute actual/policy/oracle regret across real historical races")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--n-scenarios", type=int, default=regret.DEFAULT_N_SCENARIOS)
    parser.add_argument("--seed", type=int, default=regret.DEFAULT_POLICY_SEED)
    args = parser.parse_args()

    report = run(args.processed_dir, args.n_scenarios, args.seed)
    out_path = args.processed_dir / REPORT_FILENAME
    report.to_csv(out_path, index=False)

    mean_actual_regret = report["actual_regret_seconds"].mean()
    mean_policy_regret = report["policy_regret_seconds"].mean()
    captured_fraction = 1 - (mean_policy_regret / mean_actual_regret) if mean_actual_regret > 0 else float("nan")

    print(f"evaluated {len(report)} driver-races -> {out_path}")
    print(f"mean actual regret vs. oracle: {mean_actual_regret:.2f}s")
    print(f"mean policy regret vs. oracle: {mean_policy_regret:.2f}s")
    print(f"policy captured {captured_fraction:.1%} of the value perfect information was worth over what actually happened")

    laps = pd.read_parquet(args.processed_dir / "laps.parquet")
    results = pd.read_parquet(args.processed_dir / "results.parquet")
    try:
        seconds_per_position = position_gap.estimate_seconds_per_position(laps, results)
        print(
            f"perfect information was worth {mean_actual_regret / seconds_per_position:.2f} positions per race "
            f"(at {seconds_per_position:.1f}s/position, from real finishing gaps)"
        )
    except ValueError as exc:
        print(f"skipped position-equivalent conversion: {exc}")


if __name__ == "__main__":
    main()
