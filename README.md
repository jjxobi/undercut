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

## strategy studio

`studio/` is a small React frontend for the optimizer above -- pick a
circuit, era, and race length, get back a live pit strategy, and see how
that recommendation holds up against a genuinely uncertain race (deterministic
vs. stochastic, priced on scenarios neither one optimized against). It also
shows the project's headline number: how much of the value a perfect,
after-the-fact strategy would have captured, and how much of that the policy
actually got.

It talks to the API above, not to anything bundled with it, so both need to
be running:

    uvicorn api.main:app

then, in a second terminal:

    cd studio
    npm install
    npm run dev

The studio defaults to an API at `localhost:8000`; set `VITE_API_BASE_URL`
if you're running the API somewhere else.
