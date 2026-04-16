from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modeling.degradation import circuit_variants
from modeling.degradation import features as degradation_features
from modeling.hazard import features, model

PROCESSED_DIR = Path("data/processed")
OUTPUT_FILENAME = "hazard_coefficients.csv"


def run(processed_dir: Path = PROCESSED_DIR) -> pd.DataFrame:
    laps = pd.read_parquet(processed_dir / "laps.parquet")
    track_status = pd.read_parquet(processed_dir / "track_status.parquet")
    schedule = pd.read_parquet(processed_dir / "schedule.parquet")

    circuit_laps = degradation_features.add_circuit(laps, schedule)
    signatures = circuit_variants.compute_race_signatures(circuit_laps)
    variant_map = circuit_variants.detect_variants(signatures)

    panel = features.build_hazard_panel(laps, track_status, schedule)
    panel = features.add_variant(panel, variant_map)
    panel = panel.dropna(subset=["Variant"])

    return model.fit_hazard_model(panel)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit the hierarchical safety-car hazard model")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    out_path = args.out if args.out is not None else args.processed_dir / OUTPUT_FILENAME
    coefficients = run(args.processed_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    coefficients.to_csv(out_path, index=False)
    print(f"fit hazard model with {len(coefficients)} rows -> {out_path}")
    print(coefficients.to_string())


if __name__ == "__main__":
    main()
