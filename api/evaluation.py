from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/evaluation/summary")
def evaluation_summary(request: Request) -> dict:
    report_path = request.app.state.data_dir / "regret_report.csv"
    if not report_path.exists():
        raise HTTPException(
            status_code=503,
            detail="regret_report.csv not found -- run scripts/run_evaluation.py first",
        )

    report = pd.read_csv(report_path)
    mean_actual = report["actual_regret_seconds"].mean()
    mean_policy = report["policy_regret_seconds"].mean()
    captured_fraction = 1 - (mean_policy / mean_actual) if mean_actual > 0 else float("nan")

    return {
        "driver_races": len(report),
        "mean_actual_regret_seconds": float(mean_actual),
        "median_actual_regret_seconds": float(report["actual_regret_seconds"].median()),
        "mean_policy_regret_seconds": float(mean_policy),
        "median_policy_regret_seconds": float(report["policy_regret_seconds"].median()),
        "captured_fraction": float(captured_fraction),
    }
