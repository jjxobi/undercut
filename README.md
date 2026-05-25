# dispatch

F1 race strategy under safety-car uncertainty. Built on a tyre degradation
model and a safety-car hazard model, both fit on real lap data pulled
through the pipeline, plus a smaller circuit-level model of how much
finishing order scatters from the grid (fit on race results, not lap data,
and not yet wired into the optimizer below). On top of the degradation and
hazard models sits a CP-SAT pit-strategy optimizer that has to commit to a
pit plan before knowing when the safety car comes out.

`scripts/run_optimizer.py` runs the optimizer end to end for a given
circuit and race length: it builds a "deterministic" plan (optimized
assuming no safety car) and a "stochastic" plan (optimized across sampled
safety-car scenarios), then scores both against a held-out scenario set to
see whether hedging actually paid off.

## setup

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e ".[dev]"
    pytest
