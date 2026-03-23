import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from modeling.degradation import model

DRIVERS = ["VER", "HAM", "LEC"]


def _generate_circuit_laps(
    circuit_id: str,
    true_slope: float,
    n_races: int,
    noise_sd: float,
    rng: np.random.Generator,
    max_tyre_life: int = 20,
    compound: str = "MEDIUM",
    era: str = "2022-2025 ground-effect",
    squared_coef: float = 0.002,
) -> list[dict]:
    # Generative model, already expressed in fuel-corrected terms (as
    # features.build_training_frame's CorrectedLapTimeSeconds would produce):
    # 90s base + true_slope s/lap tyre degradation (linear, the per-circuit
    # "true" rate a hierarchical fit should partially recover) + a fixed
    # population-level quadratic term + track temp + a driver offset.
    rows = []
    for race in range(n_races):
        for driver in DRIVERS:
            base_temp = 30 + rng.normal(0, 2)
            # one continuous stint per race/driver in these fixtures -- unique
            # enough that the stint-level variance component in model.py has
            # something real to key off of, without needing to model actual
            # in-race stint splits (that's what tests/test_fit_degradation_model.py's
            # two-stint fixture is for).
            stint_key = f"{era}_{circuit_id}_{race}_{driver}"
            for lap in range(1, max_tyre_life + 1):
                temp = base_temp + rng.normal(0, 0.5)
                noise = rng.normal(0, noise_sd)
                corrected = (
                    90
                    + true_slope * lap
                    + squared_coef * lap**2
                    + 0.02 * temp
                    + (2.0 if driver == "HAM" else 0.0)
                    + noise
                )
                rows.append(
                    {
                        "Compound": compound,
                        "CircuitId": circuit_id,
                        "Driver": driver,
                        "TyreLife": float(lap),
                        "TyreLifeSquared": float(lap**2),
                        "TrackTemp": temp,
                        "CorrectedLapTimeSeconds": corrected,
                        "RegulationEra": era,
                        "StintKey": stint_key,
                        # these fixtures don't model layout changes -- a single
                        # variant per circuit is exactly what a "no change ever
                        # detected" circuit looks like in real output.
                        "Variant": f"{circuit_id}_v0",
                    }
                )
    return rows


class _FakeMixedFit:
    """Minimal stand-in exposing just the attributes _is_internally_consistent reads."""

    def __init__(self, tau: float, blup_values: list[float]):
        self.cov_re = pd.DataFrame([[tau**2]], index=["TyreLife"], columns=["TyreLife"])
        self.random_effects = {
            f"circuit_{i}": {"TyreLife": value} for i, value in enumerate(blup_values)
        }


def test_is_internally_consistent_rejects_mismatched_tau_and_accepts_matching_tau():
    # Numbers mirror a real mismatch found on 2018-2021 HARD: lbfgs reported an
    # internal tau of 1.757 while the actual fitted circuit deviations (BLUPs)
    # had a std of only 0.129 -- a >13x mismatch signaling a bad local optimum,
    # even though the solver self-reported convergence. cg/powell landed on a
    # better optimum with tau=0.132, matching the BLUP spread almost exactly.
    blup_values = [0.129, -0.129]  # std == 0.129, matching the real BLUP spread

    bad_optimum = _FakeMixedFit(tau=1.757, blup_values=blup_values)
    assert not model._is_internally_consistent(bad_optimum)

    good_optimum = _FakeMixedFit(tau=0.132, blup_values=blup_values)
    assert model._is_internally_consistent(good_optimum)


def test_fit_degradation_models_recovers_population_coefficient_with_partial_pooling():
    # 5 circuits, true per-circuit slopes clustered tightly around a
    # population value of 0.08 (small per-circuit deviations) -- enough
    # circuits and enough laps per circuit for mixedlm to estimate a
    # meaningful random-slope variance component and converge reliably.
    rng = np.random.default_rng(7)
    population_true_slope = 0.08
    deviations = rng.normal(0, 0.01, size=5)
    rows = []
    for i, deviation in enumerate(deviations):
        rows += _generate_circuit_laps(f"circuit_{i}", population_true_slope + deviation, 8, 0.15, rng)
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=500)

    pooled_rows = results[results["scope"] == "pooled"]
    assert len(pooled_rows) == 1
    assert abs(pooled_rows.iloc[0]["tyre_life_coef"] - population_true_slope) < 0.03

    circuit_rows = results[results["scope"] == "circuit"]
    assert set(circuit_rows["circuit_id"]) == {f"circuit_{i}" for i in range(5)}


def test_fit_degradation_models_shrinks_sparse_circuit_toward_population():
    # 6 well-behaved circuits (480 laps each, full tyre-life range 1-20,
    # true slope near the population value of 0.08) alongside one
    # deliberately sparse, noisy circuit: only 3 short races (max tyre life
    # 5, well under the others' 20) with much higher noise and a true slope
    # (0.30) far from the population. The restricted tyre-life range and
    # elevated noise make that circuit's own-data estimate genuinely
    # unreliable, which is exactly when partial pooling should pull the
    # fitted value toward the population mean.
    #
    # To prove shrinkage happened (not just that the model ran), compare
    # the hierarchical fit's circuit-level estimate against what a plain,
    # unpooled OLS regression on that circuit's data alone would say -- the
    # unpooled estimate is this fixture's noisy, small-sample truth, and the
    # hierarchical estimate should land measurably closer to the population
    # value than that unpooled estimate does.
    rng = np.random.default_rng(24)
    rows = []
    for i in range(6):
        rows += _generate_circuit_laps(f"circuit_{i}", 0.08, 8, 0.15, rng)
    sparse_rows = _generate_circuit_laps(
        "sparse_circuit", 0.30, 3, 0.6, rng, max_tyre_life=5
    )
    rows += sparse_rows
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=500)

    population_coef = results[results["scope"] == "pooled"].iloc[0]["tyre_life_coef"]
    sparse_row = results[results["circuit_id"] == "sparse_circuit"].iloc[0]
    hierarchical_coef = sparse_row["tyre_life_coef"]

    sparse_frame = pd.DataFrame(sparse_rows)
    unpooled_fit = smf.ols(
        "CorrectedLapTimeSeconds ~ TyreLife + TyreLifeSquared + TrackTemp + C(Driver)", data=sparse_frame
    ).fit()
    unpooled_coef = unpooled_fit.params["TyreLife"]

    assert abs(hierarchical_coef - population_coef) < abs(unpooled_coef - population_coef)


def test_fit_degradation_models_keeps_extreme_circuit_estimate_without_rejecting_it():
    # One circuit with a strongly negative true slope (-0.15) and plenty of
    # low-noise data (as much as the well-behaved circuits get) -- enough
    # data that the hierarchical fit doesn't fully shrink its estimate away
    # from that negative slope, so its shrunk coefficient stays unusual
    # (likely still negative or close to it). model.py no longer rejects or
    # replaces this: it has no plausibility gate at all any more -- it's
    # predict.degradation_seconds's job to make any stored coefficient safe
    # to query, not fit_degradation_models's job to filter what gets stored.
    # This asserts the circuit still gets its own row, with its own (not the
    # population's) coefficient, proving nothing is being silently rejected.
    rng = np.random.default_rng(1)
    rows = _generate_circuit_laps("problem_circuit", -0.15, 8, 0.15, rng)
    for i in range(5):
        rows += _generate_circuit_laps(f"circuit_{i}", 0.08, 8, 0.15, rng)
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=500)

    pooled_row = results[results["scope"] == "pooled"].iloc[0]
    problem_row = results[results["circuit_id"] == "problem_circuit"]

    assert len(problem_row) == 1
    problem_row = problem_row.iloc[0]
    # its own shrunk estimate is stored, not silently swapped for the population's
    assert problem_row["tyre_life_coef"] != pooled_row["tyre_life_coef"]
    # and it's still meaningfully different (extreme relative to the other circuits),
    # confirming this wasn't fully shrunk away either
    assert problem_row["tyre_life_coef"] < pooled_row["tyre_life_coef"] - 0.05


def test_fit_degradation_models_skips_group_with_too_few_circuits():
    # Two circuits, plenty of laps each (well past the total-lap floor) --
    # but a hierarchical fit needs enough distinct circuits to estimate a
    # meaningful random-effects variance component, and 2 is below the
    # minimum of 3. The group should be skipped entirely: zero rows, not an
    # error and not a degenerate fit.
    rows = []
    for circuit in ["bahrain", "monza"]:
        for i in range(300):
            tyre_life = float((i % 20) + 1)
            rows.append(
                {
                    "Compound": "MEDIUM",
                    "CircuitId": circuit,
                    "Driver": "VER",
                    "TyreLife": tyre_life,
                    "TyreLifeSquared": tyre_life**2,
                    "TrackTemp": 30.0,
                    "CorrectedLapTimeSeconds": 90.0 + 0.08 * tyre_life,
                    "RegulationEra": "2022-2025 ground-effect",
                    "StintKey": f"{circuit}_{i}",
                    "Variant": f"{circuit}_v0",
                }
            )
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=500)

    assert len(results) == 0


def test_fit_degradation_models_skips_group_with_too_few_laps():
    # Four circuits (enough circuits), but only 20 laps apiece -- well
    # under the 500-lap floor for the whole group. Should also skip
    # cleanly rather than attempting an underpowered hierarchical fit.
    rows = []
    for circuit in ["bahrain", "monza", "imola", "spa"]:
        for i in range(20):
            tyre_life = float((i % 20) + 1)
            rows.append(
                {
                    "Compound": "MEDIUM",
                    "CircuitId": circuit,
                    "Driver": "VER",
                    "TyreLife": tyre_life,
                    "TyreLifeSquared": tyre_life**2,
                    "TrackTemp": 30.0,
                    "CorrectedLapTimeSeconds": 90.0 + 0.08 * tyre_life,
                    "RegulationEra": "2022-2025 ground-effect",
                    "StintKey": f"{circuit}_{i}",
                    "Variant": f"{circuit}_v0",
                }
            )
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=500)

    assert len(results) == 0


def test_fit_degradation_models_stratifies_by_regulation_era():
    # Same compound and same four circuits (including a shared "bahrain")
    # across two eras with different population-level true slopes. Each
    # era/compound group should get its own pooled fit, and the shared
    # circuit should get two separate circuit-level rows -- one per era --
    # each landing near that era's population value, never conflated across
    # the regulation change.
    rng = np.random.default_rng(3)
    era_a_specs = [("bahrain", 0.06), ("monza", 0.058), ("imola", 0.062), ("spa", 0.059)]
    era_b_specs = [("bahrain", 0.10), ("monza", 0.098), ("imola", 0.102), ("spa", 0.099)]

    rows = []
    for circuit_id, true_slope in era_a_specs:
        rows += _generate_circuit_laps(circuit_id, true_slope, 8, 0.15, rng, era="2018-2021 aero")
    for circuit_id, true_slope in era_b_specs:
        rows += _generate_circuit_laps(
            circuit_id, true_slope, 8, 0.15, rng, era="2022-2025 ground-effect"
        )
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=500)

    assert set(results["era"]) == {"2018-2021 aero", "2022-2025 ground-effect"}

    pooled_a = results[(results["era"] == "2018-2021 aero") & (results["scope"] == "pooled")].iloc[0]
    pooled_b = results[
        (results["era"] == "2022-2025 ground-effect") & (results["scope"] == "pooled")
    ].iloc[0]
    assert abs(pooled_a["tyre_life_coef"] - 0.06) < 0.03
    assert abs(pooled_b["tyre_life_coef"] - 0.10) < 0.03

    bahrain_rows = results[results["circuit_id"] == "bahrain"]
    assert len(bahrain_rows) == 2
    assert set(bahrain_rows["era"]) == {"2018-2021 aero", "2022-2025 ground-effect"}
    bahrain_a = bahrain_rows[bahrain_rows["era"] == "2018-2021 aero"].iloc[0]
    bahrain_b = bahrain_rows[bahrain_rows["era"] == "2022-2025 ground-effect"].iloc[0]
    assert bahrain_a["tyre_life_coef"] < bahrain_b["tyre_life_coef"]


def test_fit_degradation_models_returns_typed_empty_frame_when_nothing_qualifies():
    frame = pd.DataFrame(
        columns=[
            "TyreLife",
            "TyreLifeSquared",
            "TrackTemp",
            "CorrectedLapTimeSeconds",
            "CircuitId",
            "Compound",
            "RegulationEra",
            "Driver",
            "StintKey",
            "Variant",
        ]
    )

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=500)

    assert len(results) == 0
    assert list(results.columns) == [
        "era",
        "compound",
        "scope",
        "circuit_id",
        "n_obs",
        "r_squared",
        "tyre_life_coef",
        "tyre_life_squared_coef",
        "tyre_life_pvalue",
    ]
