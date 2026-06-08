from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/circuits")
def list_circuits(request: Request) -> dict:
    state = request.app.state
    circuits = [
        {"circuit_id": circuit_id, "default_race_length": state.default_race_lengths[circuit_id]}
        for circuit_id in sorted(state.known_circuit_ids)
        if circuit_id in state.default_race_lengths
    ]
    return {"circuits": circuits, "eras": sorted(state.known_eras)}
