from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from modeling.evaluation import position_gap

router = APIRouter()


class EvaluationSummaryResponse(BaseModel):
    driver_races: int
    mean_actual_regret_seconds: float
    median_actual_regret_seconds: float
    mean_policy_regret_seconds: float
    median_policy_regret_seconds: float
    captured_fraction: float
    mean_regret_positions_per_race: float | None = None


@router.get("/evaluation/summary", response_model=EvaluationSummaryResponse)
def evaluation_summary(request: Request) -> EvaluationSummaryResponse:
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

    try:
        seconds_per_position = position_gap.estimate_seconds_per_position(request.app.state.laps, request.app.state.results)
        positions_per_race = mean_actual / seconds_per_position
    except ValueError:
        positions_per_race = None

    return EvaluationSummaryResponse(
        driver_races=len(report),
        mean_actual_regret_seconds=float(mean_actual),
        median_actual_regret_seconds=float(report["actual_regret_seconds"].median()),
        mean_policy_regret_seconds=float(mean_policy),
        median_policy_regret_seconds=float(report["policy_regret_seconds"].median()),
        captured_fraction=float(captured_fraction),
        mean_regret_positions_per_race=positions_per_race,
    )
