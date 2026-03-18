from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modeling.degradation import features, filters, model

PROCESSED_DIR = Path("data/processed")
OUTPUT_FILENAME = "degradation_coefficients.csv"


def run(
    processed_dir: Path = PROCESSED_DIR,
    min_laps_for_circuit_model: int = model.MIN_LAPS_FOR_CIRCUIT_MODEL,
) -> pd.DataFrame:
    laps = pd.read_parquet(processed_dir / "laps.parquet")
    schedule = pd.read_parquet(processed_dir / "schedule.parquet")
    weather = pd.read_parquet(processed_dir / "weather.parquet")

    accurate = filters.accurate_laps(laps)
    training_frame = features.build_training_frame(accurate, schedule, weather)
    training_frame = filters.exclude_rain_affected_dry_compound_laps(training_frame)

    return model.fit_degradation_models(training_frame, min_laps_for_circuit_model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit fuel-corrected tyre degradation models")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--min-laps", type=int, default=model.MIN_LAPS_FOR_CIRCUIT_MODEL)
    args = parser.parse_args()

    out_path = args.out if args.out is not None else args.processed_dir / OUTPUT_FILENAME
    coefficients = run(args.processed_dir, args.min_laps)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    coefficients.to_csv(out_path, index=False)
    print(f"fit {len(coefficients)} degradation models -> {out_path}")
    print(coefficients[["compound", "scope", "circuit_id", "n_obs", "r_squared", "tyre_life_coef"]].to_string())


if __name__ == "__main__":
    main()
