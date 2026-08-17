from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from api.compare import CompareResponse
from api.compare import PlanSummary as ComparePlanSummary
from api.strategy import StrategyResponse
from modeling import config
from modeling.optimization import comparison, pit_loss, scenarios, strategy

PROCESSED_DIR = Path("data/processed")
OUTPUT_FILENAME = "warm_cache.json"

# must match ControlPanel.tsx's default scenario count and ComparePanel.tsx's
# fixed scenario count/seed -- these are the exact cache keys a first-time
# visitor hits before touching any input, so warming anything else is wasted
STRATEGY_N_SCENARIOS = 200
COMPARE_N_SCENARIOS = 80
SEED = 0

KEY_SEP = "|"


def cache_key(circuit_id: str, era: str, race_length: int, n_scenarios: int, seed: int) -> str:
    return KEY_SEP.join([circuit_id, era, str(race_length), str(n_scenarios), str(seed)])


def parse_cache_key(key: str) -> tuple[str, str, int, int, int]:
    circuit_id, era, race_length, n_scenarios, seed = key.split(KEY_SEP)
    return (circuit_id, era, int(race_length), int(n_scenarios), int(seed))


def _default_race_lengths(laps: pd.DataFrame, schedule: pd.DataFrame) -> dict[str, int]:
    # mirrors api/main.py's own derivation so the warm cache is keyed on
    # exactly the same default race length /circuits would hand the frontend
    race_lengths = laps.groupby(["Season", "Round"])["LapNumber"].max()
    merged = race_lengths.reset_index().merge(schedule[["Season", "Round", "CircuitId"]], on=["Season", "Round"])
    latest = merged.sort_values("Season").groupby("CircuitId").last()
    return latest["LapNumber"].astype(int).to_dict()


def build(processed_dir: Path = PROCESSED_DIR) -> dict[str, dict[str, dict]]:
    degradation_coefficients = pd.read_csv(processed_dir / "degradation_coefficients.csv")
    hazard_coefficients = pd.read_csv(processed_dir / "hazard_coefficients.csv")
    laps = pd.read_parquet(processed_dir / "laps.parquet")
    schedule = pd.read_parquet(processed_dir / "schedule.parquet")
    pit_loss_table = pit_loss.estimate_pit_loss(laps, schedule)

    default_race_lengths = _default_race_lengths(laps, schedule)
    circuit_ids = sorted(schedule["CircuitId"].unique())
    era_names = [era["name"] for era in config.REGULATION_ERAS]

    strategy_entries: dict[str, dict] = {}
    compare_entries: dict[str, dict] = {}

    for circuit_id in circuit_ids:
        race_length = default_race_lengths.get(circuit_id)
        if race_length is None:
            continue

        circuit_pit_loss = pit_loss_table[pit_loss_table["circuit_id"] == circuit_id]
        pit_loss_seconds = (
            float(circuit_pit_loss.iloc[0]["pit_loss_seconds"])
            if len(circuit_pit_loss) > 0
            else float(pit_loss_table[pit_loss_table["circuit_id"].isna()].iloc[0]["pit_loss_seconds"])
        )

        for era in era_names:
            print(f"warming {circuit_id} / {era} / {race_length} laps...")

            try:
                sampled = scenarios.sample_scenarios(
                    STRATEGY_N_SCENARIOS, race_length, circuit_id, era,
                    hazard_coefficients, scenarios.DEFAULT_DURATION_SAMPLES, SEED,
                )
                result = strategy.optimize_strategy(
                    race_length, circuit_id, era, degradation_coefficients, sampled, pit_loss_seconds,
                )
                if result is not None:
                    response = StrategyResponse(
                        status=result["status"],
                        compounds=result["compounds"],
                        stint_lengths=result["stint_lengths"],
                        pit_laps=result["pit_laps"],
                        expected_cost_seconds=result["expected_cost_seconds"],
                        pit_loss_seconds=pit_loss_seconds,
                    )
                    key = cache_key(circuit_id, era, race_length, STRATEGY_N_SCENARIOS, SEED)
                    strategy_entries[key] = response.model_dump()
            except Exception as exc:  # noqa: BLE001 - one bad combo must not abort the warm-up
                print(f"  skip strategy {circuit_id}/{era}: {exc}")

            try:
                result = comparison.compare_deterministic_vs_stochastic(
                    degradation_coefficients, hazard_coefficients, pit_loss_table,
                    circuit_id, era, race_length, COMPARE_N_SCENARIOS, SEED,
                )
                gap = result["deterministic_evaluated_on_scenarios"] - result["stochastic_evaluated_on_scenarios"]
                gap_se = result["gap_standard_error"]
                response = CompareResponse(
                    deterministic=ComparePlanSummary(**result["deterministic"]),
                    stochastic=ComparePlanSummary(**result["stochastic"]),
                    deterministic_costs=result["deterministic_costs"],
                    stochastic_costs=result["stochastic_costs"],
                    gap_seconds=gap,
                    gap_standard_error=gap_se,
                    gap_is_significant=abs(gap) > comparison.GAP_SIGNIFICANCE_MULTIPLIER * gap_se,
                    pit_loss_seconds=result["pit_loss_seconds"],
                )
                key = cache_key(circuit_id, era, race_length, COMPARE_N_SCENARIOS, SEED)
                compare_entries[key] = response.model_dump()
            except Exception as exc:  # noqa: BLE001
                print(f"  skip compare {circuit_id}/{era}: {exc}")

    return {"strategy": strategy_entries, "compare": compare_entries}


def write(warm: dict, processed_dir: Path = PROCESSED_DIR) -> Path:
    out_path = processed_dir / OUTPUT_FILENAME
    out_path.write_text(json.dumps(warm))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Precompute solve/compare results for every circuit at its default race length"
    )
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    args = parser.parse_args()

    warm = build(args.processed_dir)
    out_path = write(warm, args.processed_dir)
    print(f"warmed {len(warm['strategy'])} strategy entries, {len(warm['compare'])} compare entries -> {out_path}")


if __name__ == "__main__":
    main()
