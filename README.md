# dispatch

F1 race strategy under safety-car uncertainty. Built on a tyre degradation
model, a safety-car hazard model, and a smaller model for how a driver's
own pace is bent by the cars around them, all fit on real lap data pulled
through the pipeline. On top of that sits a CP-SAT pit-strategy optimizer
that has to commit to a pit plan before knowing when the safety car comes
out.

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
