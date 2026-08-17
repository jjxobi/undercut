from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modeling import config
from scripts import (
    build_dataset,
    fit_degradation_model,
    fit_field_interaction_model,
    fit_hazard_model,
    run_evaluation,
    warm_cache,
)

PROCESSED_DIR = Path("data/processed")

# results come from Jolpica, laps from FastF1 -- independent sources. If
# results succeeded but laps came back mostly empty, that's the signature of
# a failed FastF1 fetch (rate limiting, a network hiccup), not a real absence
# of lap data, and merging it would silently overwrite good existing data.
MIN_LAP_COVERAGE_FRACTION = 0.5


def _season_round_pairs(frame: pd.DataFrame) -> set[tuple]:
    if "Season" not in frame.columns or "Round" not in frame.columns:
        return set()
    return set(zip(frame["Season"], frame["Round"], strict=False))


def _check_fetch_is_complete_enough(tables: dict[str, pd.DataFrame]) -> None:
    results_rounds = _season_round_pairs(tables["results"])
    laps_rounds = _season_round_pairs(tables["laps"])
    if results_rounds and len(laps_rounds) < len(results_rounds) * MIN_LAP_COVERAGE_FRACTION:
        raise RuntimeError(
            f"fetched results for {len(results_rounds)} round(s) but lap data for only {len(laps_rounds)} -- "
            "this looks like a failed FastF1 fetch, not real data. Refusing to overwrite the existing "
            "processed data with this."
        )


def refresh(processed_dir: Path = PROCESSED_DIR, seasons: list[int] | None = None) -> None:
    seasons = seasons if seasons is not None else [config.LAST_CONFIRMED_SEASON]
    print(f"pulling season(s) {seasons}...")
    tables = build_dataset.build(seasons, refresh=True)
    _check_fetch_is_complete_enough(tables)
    build_dataset.merge_and_write_tables(tables, seasons, processed_dir)

    print("fitting degradation model...")
    degradation_coefficients = fit_degradation_model.run(processed_dir)
    degradation_coefficients.to_csv(processed_dir / fit_degradation_model.OUTPUT_FILENAME, index=False)

    print("fitting hazard model...")
    hazard_coefficients = fit_hazard_model.run(processed_dir)
    hazard_coefficients.to_csv(processed_dir / fit_hazard_model.OUTPUT_FILENAME, index=False)

    print("fitting field-interaction model...")
    field_interaction_coefficients = fit_field_interaction_model.run(processed_dir)
    field_interaction_coefficients.to_csv(processed_dir / fit_field_interaction_model.OUTPUT_FILENAME, index=False)

    print("running the evaluation pass...")
    report = run_evaluation.run(processed_dir)
    report.to_csv(processed_dir / run_evaluation.REPORT_FILENAME, index=False)

    print("warming the solve/compare cache for every circuit at its default race length...")
    warm = warm_cache.build(processed_dir)
    warm_cache.write(warm, processed_dir)

    print("refresh complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-pull data and re-fit every model in one pass")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument(
        "--seasons", type=int, nargs="*", default=None,
        help="seasons to re-fetch and merge in (default: just the current season)",
    )
    args = parser.parse_args()
    refresh(args.processed_dir, args.seasons)


if __name__ == "__main__":
    main()
