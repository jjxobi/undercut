# dispatch

F1 race strategy under safety-car uncertainty. Working through a tyre
degradation model, a safety-car hazard model, and a strategy optimizer
that has to commit to a pit plan before knowing when the safety car
comes out.

Early stages right now — data pipeline first, models after.

## setup

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e ".[dev]"
    pytest
