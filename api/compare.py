from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from modeling.optimization import comparison

router = APIRouter()

MAX_CACHE_ENTRIES = 256


class CompareRequest(BaseModel):
    circuit_id: str
    era: str
    race_length: int = Field(gt=0, le=100)
    n_scenarios: int = Field(default=200, gt=0, le=2000)
    seed: int = 0


class PlanSummary(BaseModel):
    status: str
    compounds: list[str]
    stint_lengths: list[int]
    pit_laps: list[int]
    expected_cost_seconds: float


class CompareResponse(BaseModel):
    deterministic: PlanSummary
    stochastic: PlanSummary
    deterministic_costs: list[float]
    stochastic_costs: list[float]
    gap_seconds: float
    gap_standard_error: float
    gap_is_significant: bool
    pit_loss_seconds: float


@router.post("/strategy/compare", response_model=CompareResponse)
def compare_strategies(payload: CompareRequest, request: Request) -> CompareResponse:
    state = request.app.state
    if payload.circuit_id not in state.known_circuit_ids:
        raise HTTPException(status_code=404, detail=f"unknown circuit_id: {payload.circuit_id}")
    if payload.era not in state.known_eras:
        raise HTTPException(status_code=422, detail=f"unknown era: {payload.era}")

    cache = state.compare_cache
    cache_key = (payload.circuit_id, payload.era, payload.race_length, payload.n_scenarios, payload.seed)
    if cache_key in cache:
        cache.move_to_end(cache_key)
        return cache[cache_key]

    try:
        result = comparison.compare_deterministic_vs_stochastic(
            state.degradation_coefficients,
            state.hazard_coefficients,
            state.pit_loss_table,
            payload.circuit_id,
            payload.era,
            payload.race_length,
            payload.n_scenarios,
            payload.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    gap = result["deterministic_evaluated_on_scenarios"] - result["stochastic_evaluated_on_scenarios"]
    gap_se = result["gap_standard_error"]

    response = CompareResponse(
        deterministic=PlanSummary(**result["deterministic"]),
        stochastic=PlanSummary(**result["stochastic"]),
        deterministic_costs=result["deterministic_costs"],
        stochastic_costs=result["stochastic_costs"],
        gap_seconds=gap,
        gap_standard_error=gap_se,
        gap_is_significant=abs(gap) > comparison.GAP_SIGNIFICANCE_MULTIPLIER * gap_se,
        pit_loss_seconds=result["pit_loss_seconds"],
    )
    cache[cache_key] = response
    if len(cache) > MAX_CACHE_ENTRIES:
        cache.popitem(last=False)
    return response
