from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class CircuitInfo(BaseModel):
    circuit_id: str
    default_race_length: int


class CircuitsResponse(BaseModel):
    circuits: list[CircuitInfo]
    eras: list[str]


@router.get("/circuits", response_model=CircuitsResponse)
def list_circuits(request: Request) -> CircuitsResponse:
    state = request.app.state
    circuits = [
        CircuitInfo(circuit_id=circuit_id, default_race_length=state.default_race_lengths[circuit_id])
        for circuit_id in sorted(state.known_circuit_ids)
        if circuit_id in state.default_race_lengths
    ]
    return CircuitsResponse(circuits=circuits, eras=sorted(state.known_eras))
