# dispatch

F1 pit strategy under safety-car uncertainty. The core idea: a good strategy
has to commit to a pit plan before knowing whether a safety car shows up, so
the interesting question isn't "what was the optimal strategy for this race"
(easy, in hindsight) but "how much better could a strategy have done given
only what was knowable at the time."

The project is built in layers, each fit on real data pulled through the
pipeline in `modeling/ingest`:

- a tyre degradation model (mixed-effects, per compound and era, pooled
  across circuits with circuit-level random effects)
- a safety-car hazard model (how likely is a safety car on a given lap of a
  given circuit)
- a smaller field-interaction model of how much finishing order scatters
  from the grid, fit on race results rather than lap data
- a CP-SAT pit-strategy optimizer that sits on top of the first two and
  produces both a "deterministic" plan (optimized assuming no safety car)
  and a "stochastic" plan (optimized across sampled safety-car scenarios)
- an evaluation layer that scores both plans against a held-out scenario
  set and against what actually happened, to see whether hedging paid off

`studio/` is a live frontend on top of all of it -- pick a circuit, era, and
race length, and get back a real strategy solve.

## the headline result

For every driver-race where the driver's actual compound sequence and stint
lengths matched one of the strategies the optimizer is even capable of
proposing (652 driver-races total), `data/processed/regret_report.csv`
compares three things: what the driver actually ran, what the stochastic
policy would have recommended, and what a perfect, after-the-fact strategy
(one that knew exactly when the safety car would come out) would have run.

Averaged across those 652 driver-races:

- perfect information was worth **16.77 seconds** per driver-race over what
  actually happened (mean actual regret)
- the stochastic policy's own regret against that same perfect-information
  benchmark is **6.17 seconds**
- so the policy captured about **63%** of the value that hindsight had
  available to give

That's the number the studio's headline stat and `/evaluation/summary`
are built around. It's not "the optimizer is nearly as good as knowing the
future" -- it's "committing to a plan that hedges against safety-car risk,
instead of just running what everyone else runs, recovers most of the gap
between the average driver-race and the best possible one."

## architecture

    modeling/
      ingest/          pulls lap, stint, pit-stop, and result data via
                        FastF1 and Jolpica
      degradation/      the tyre model: feature engineering, the mixed
                        model itself, per-circuit lookup
      hazard/           the safety-car model
      field_interaction/ the position-scatter model
      optimization/     the CP-SAT solver, candidate strategy search,
                        pit-loss estimation, scenario sampling
      evaluation/       regret scoring against real and simulated outcomes
      analysis/         one-off diagnostics (hazard model sample sizes etc.)
    api/                a FastAPI service that loads the fitted models once
                        at startup and serves circuits, strategy solves, the
                        deterministic-vs-stochastic comparison, and the
                        regret summary
    studio/             the React frontend
    scripts/            build_dataset.py, fit_*.py, run_optimizer.py,
                        run_evaluation.py, and refresh.py, which chains all
                        of them into one command
    notebooks/          the regret report and the deterministic-vs-stochastic
                        demo, as notebooks rather than one-off scripts
    data/
      raw/              FastF1 cache, gitignored
      processed/        the tables and fitted coefficients everything above
                        reads from -- tracked in git (see limitations)

## honest limitations

- the degradation model corrects for fuel burn with a flat constant
  (`FUEL_S_PER_LAP = 0.07`) rather than a fitted per-race fuel-load curve.
  it's a reasonable approximation, not a measured one.
- `mean_position_delta` in the field-interaction model is systematically
  positive and correlates with each circuit's retirement rate, not with how
  hard it is to overtake there -- it's a survivorship artifact of only
  looking at classified finishers (a retirement ahead of you bumps everyone
  behind up a place without anyone passing anyone). the model's own module
  docstring flags this explicitly and says not to read it as "positions
  gained by racecraft." `position_delta_sd`, the shrinkage-adjusted spread,
  is the statistic that's actually validated and used.
- that same model also pools on raw circuit id rather than the layout-variant
  ids the degradation model uses, a deliberate simplification with a known
  small effect (Bahrain's 2020 Sakhir layout folded into normal Bahrain,
  about a 2.6% difference on that one case).
- `PIT_LOSS_SC_FRACTION` (how much cheaper a pit stop is under a safety car)
  is a flat 0.3 in the solver -- a documented assumption, not a value fit
  from pit-loss data.
- the actual-strategy comparison only includes driver-races whose real
  compound sequence exactly matches one of the optimizer's five candidate
  sequences and whose stint lengths all clear the minimum stint length --
  races run on strategies outside that set (extra splash-and-dash stops,
  five-stop wet races, whatever) are dropped from the regret report
  entirely, not scored against it.
- the API has no authentication and no rate limiting. fine for a small
  portfolio deployment serving read-mostly, precomputed-and-cached results;
  not something to point at production traffic.
- `data/processed/` is tracked in git so the Docker image and a fresh clone
  are self-contained. the tradeoff is that every weekly refresh commits
  changed parquet/csv files as binary diffs, so the history accumulates
  data snapshots alongside code changes. acceptable for now; would want
  git-lfs or an external artifact store if this ever needed to scale past
  a few years of refreshes.

## local development

backend:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e ".[dev]"
    pytest
    uvicorn api.main:app

frontend, in a second terminal:

    cd studio
    npm install
    npm run dev

the studio talks to the API, not to anything bundled with it, so both need
to be running. it defaults to an API at `localhost:8000`; set
`VITE_API_BASE_URL` if you're running the API somewhere else.

pick a circuit, era, and race length in the studio and get back a live pit
strategy, plus how that recommendation holds up against a genuinely
uncertain race (deterministic vs. stochastic, priced on scenarios neither
one optimized against) and the headline regret-captured stat above.

to re-pull data and re-fit everything from scratch in one pass:

    python scripts/refresh.py

## deployment

the repo is set up to deploy, though nothing is deployed from it yet:

- `Dockerfile` builds a self-contained API image -- it bakes in
  `data/processed/` so the container doesn't need a data volume or a
  startup fetch, just `uvicorn api.main:app`.
- `render.yaml` is a Render blueprint pointing at that Dockerfile with a
  `/health` check.
- `studio/vercel.json` builds and serves the studio frontend as a static
  site (`npm run build`, `dist/`).
- `.github/workflows/refresh.yml` re-runs `scripts/refresh.py` on a weekly
  cron and commits `data/processed/` if anything changed, so a deployed
  Render instance can pick up a fresh fit on redeploy.
- `.github/workflows/ci.yml` runs the backend (`ruff`, `pytest`) and
  frontend (`tsc`, `vitest`, `npm run build`) checks on every push and PR.

actually wiring up the Render/Vercel services, connecting them to a GitHub
remote, and setting secrets is the next step, not something this repo does
by itself.
