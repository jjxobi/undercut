from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modeling.field_interaction import model, position_outcomes

PROCESSED_DIR = Path("data/processed")
OUTPUT_FILENAME = "field_interaction_coefficients.csv"


def run(processed_dir: Path = PROCESSED_DIR) -> pd.DataFrame:
    results = pd.read_parquet(processed_dir / "results.parquet")
    schedule = pd.read_parquet(processed_dir / "schedule.parquet")

    frame = position_outcomes.build_position_change_frame(results, schedule)
    return model.fit_position_volatility(frame)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fit the circuit position-volatility (field-interaction) model"
    )
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    out_path = args.out if args.out is not None else args.processed_dir / OUTPUT_FILENAME
    coefficients = run(args.processed_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    coefficients.to_csv(out_path, index=False)
    print(f"fit position-volatility model with {len(coefficients)} rows -> {out_path}")
    print(coefficients.sort_values("position_delta_sd").to_string())


if __name__ == "__main__":
    main()
