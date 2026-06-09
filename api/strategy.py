from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from modeling.optimization import scenarios, strategy

router = APIRouter()


class StrategyRequest(BaseModel):
    circuit_id: str
    era: str
    race_length: int = Field(gt=0)
    n_scenarios: int = Field(default=200, gt=0)
    seed: int = 0


class StrategyResponse(BaseModel):
    status: str
    compounds: list[str]
    stint_lengths: list[int]
    pit_laps: list[int]
    expected_cost_seconds: float
    pit_loss_seconds: float


@router.post("/strategy", response_model=StrategyResponse)
def solve_strategy(payload: StrategyRequest, request: Request) -> StrategyResponse:
    state = request.app.state
    if payload.circuit_id not in state.known_circuit_ids:
        raise HTTPException(status_code=404, detail=f"unknown circuit_id: {payload.circuit_id}")
    if payload.era not in state.known_eras:
        raise HTTPException(status_code=422, detail=f"unknown era: {payload.era}")

    cache_key = (payload.circuit_id, payload.era, payload.race_length, payload.n_scenarios, payload.seed)
    if cache_key in state.strategy_cache:
        return state.strategy_cache[cache_key]

    pit_loss_table = state.pit_loss_table
    circuit_pit_loss = pit_loss_table[pit_loss_table["circuit_id"] == payload.circuit_id]
    pit_loss_seconds = (
        float(circuit_pit_loss.iloc[0]["pit_loss_seconds"])
        if len(circuit_pit_loss) > 0
        else float(pit_loss_table[pit_loss_table["circuit_id"].isna()].iloc[0]["pit_loss_seconds"])
    )

    sampled_scenarios = scenarios.sample_scenarios(
        payload.n_scenarios,
        payload.race_length,
        payload.circuit_id,
        payload.era,
        state.hazard_coefficients,
        scenarios.DEFAULT_DURATION_SAMPLES,
        payload.seed,
    )
    result = strategy.optimize_strategy(
        payload.race_length,
        payload.circuit_id,
        payload.era,
        state.degradation_coefficients,
        sampled_scenarios,
        pit_loss_seconds,
    )
    if result is None:
        raise HTTPException(
            status_code=422, detail=f"no feasible strategy for a {payload.race_length}-lap race"
        )

    response = StrategyResponse(
        status=result["status"],
        compounds=result["compounds"],
        stint_lengths=result["stint_lengths"],
        pit_laps=result["pit_laps"],
        expected_cost_seconds=result["expected_cost_seconds"],
        pit_loss_seconds=pit_loss_seconds,
    )
    state.strategy_cache[cache_key] = response
    return response
