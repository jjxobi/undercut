from __future__ import annotations

import argparse
from pathlib import Path

from modeling import config
from scripts import (
    build_dataset,
    fit_degradation_model,
    fit_field_interaction_model,
    fit_hazard_model,
    run_evaluation,
)

PROCESSED_DIR = Path("data/processed")


def refresh(processed_dir: Path = PROCESSED_DIR, seasons: list[int] | None = None) -> None:
    seasons = seasons if seasons is not None else [config.LAST_CONFIRMED_SEASON]
    print(f"pulling season(s) {seasons}...")
    tables = build_dataset.build(seasons, refresh=True)
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
