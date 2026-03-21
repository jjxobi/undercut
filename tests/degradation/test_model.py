import numpy as np
import pandas as pd

from modeling.degradation import model


def _synthetic_frame(
    compound: str = "MEDIUM", tyre_life_coef: float = 0.08, era: str = "2022-2025 ground-effect"
) -> pd.DataFrame:
    # True generative model, expressed directly in already-fuel-corrected terms
    # (as features.build_training_frame's CorrectedLapTimeSeconds would produce):
    # 90s base + tyre_life_coef s/lap tyre degradation (linear) + 0.002 s/lap^2
    # (mild quadratic) + 0.02 s/degree track temp + a 2s driver offset for one
    # driver. No RaceLapNumber/fuel term is needed here since the a-priori
    # fuel correction is assumed to already have removed it from
    # CorrectedLapTimeSeconds -- that's the whole point of correcting before
    # fitting instead of estimating the fuel effect as a free regressor.
    # bahrain gets enough races to be "credible" on its own. monaco and imola
    # each stay individually sparse (well under the 300-lap credibility bar),
    # but combined they clear the pooling threshold, so together they produce
    # a single pooled fit rather than being dropped for lack of data.
    rng = np.random.default_rng(42)
    rows = []
    drivers = ["VER", "HAM", "LEC"]
    for circuit, n_races in [("bahrain", 40), ("monaco", 3), ("imola", 3)]:
        for race in range(n_races):
            for driver in drivers:
                base_temp = 30 + rng.normal(0, 2)
                for lap in range(1, 21):
                    tyre_life = lap
                    temp = base_temp + rng.normal(0, 0.5)
                    noise = rng.normal(0, 0.15)
                    corrected = (
                        90
                        + tyre_life_coef * tyre_life
                        + 0.002 * tyre_life**2
                        + 0.02 * temp
                        + (2.0 if driver == "HAM" else 0.0)
                        + noise
                    )
                    rows.append(
                        {
                            "Compound": compound,
                            "CircuitId": circuit,
                            "Driver": driver,
                            "TyreLife": tyre_life,
                            "TyreLifeSquared": tyre_life**2,
                            "TrackTemp": temp,
                            "CorrectedLapTimeSeconds": corrected,
                            "RegulationEra": era,
                        }
                    )
    return pd.DataFrame(rows)


def test_fit_degradation_models_recovers_true_coefficient_for_credible_circuit():
    frame = _synthetic_frame()

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    bahrain_row = results[(results.scope == "circuit") & (results.circuit_id == "bahrain")].iloc[0]
    assert abs(bahrain_row["tyre_life_coef"] - 0.08) < 0.02
    assert bahrain_row["r_squared"] > 0.8
    assert bahrain_row["tyre_life_pvalue"] < 0.01
    assert bahrain_row["compound"] == "MEDIUM"
    assert bahrain_row["era"] == "2022-2025 ground-effect"


def test_fit_degradation_models_pools_sparse_circuit():
    frame = _synthetic_frame()

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    pooled_rows = results[results.scope == "pooled"]
    assert len(pooled_rows) == 1
    assert pooled_rows.iloc[0]["circuit_id"] is None
    circuit_rows = results[results.scope == "circuit"]
    assert list(circuit_rows["circuit_id"]) == ["bahrain"]


def test_fit_degradation_models_handles_multiple_compounds_independently():
    # SOFT's true tyre-age slope (0.12) is deliberately different from MEDIUM's
    # (0.08) rather than merely offset by a constant, so an implementation that
    # accidentally pools/entangles the two compounds (e.g. fits once on the
    # concatenated frame and stamps both labels onto the same result rows)
    # would recover a single slope for both and fail the assertions below.
    medium = _synthetic_frame(compound="MEDIUM", tyre_life_coef=0.08)
    soft = _synthetic_frame(compound="SOFT", tyre_life_coef=0.12)
    frame = pd.concat([medium, soft], ignore_index=True)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    assert set(results["compound"]) == {"MEDIUM", "SOFT"}
    assert len(results) == 4  # 2 compounds x (1 circuit-credible + 1 pooled) each

    medium_bahrain = results[
        (results.compound == "MEDIUM") & (results.scope == "circuit") & (results.circuit_id == "bahrain")
    ].iloc[0]
    soft_bahrain = results[
        (results.compound == "SOFT") & (results.scope == "circuit") & (results.circuit_id == "bahrain")
    ].iloc[0]

    assert abs(medium_bahrain["tyre_life_coef"] - soft_bahrain["tyre_life_coef"]) > 0.02
    assert medium_bahrain["n_obs"] == 2400
    assert soft_bahrain["n_obs"] == 2400


def test_fit_degradation_models_skips_pooled_fit_below_credibility_threshold():
    # Many circuits, one lap each: nowhere near enough total data to trust a
    # pooled fit, even though each individual circuit is far too sparse to
    # get its own circuit-specific model. Without a minimum-observation guard,
    # statsmodels will still "succeed" on this rank-deficient design via a
    # pseudo-inverse and return a perfect-looking but meaningless fit.
    rows = []
    for i in range(30):
        rows.append(
            {
                "Compound": "WET",
                "CircuitId": f"circuit_{i}",
                "Driver": "VER",
                "TyreLife": 1,
                "TyreLifeSquared": 1,
                "TrackTemp": 25.0,
                "CorrectedLapTimeSeconds": 100.0 + i,
                "RegulationEra": "2022-2025 ground-effect",
            }
        )
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    assert len(results[results["compound"] == "WET"]) == 0


def test_fit_degradation_models_returns_typed_empty_frame_when_nothing_qualifies():
    frame = _synthetic_frame()

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=1_000_000)

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


def test_fit_degradation_models_rejects_implausible_circuit_fit_and_falls_back_to_pooled():
    # bahrain: enough laps to be circuit-credible, but constructed with a
    # NEGATIVE true tyre-age slope (tyres get faster -- physically impossible).
    # imola: also enough laps, with a normal POSITIVE true slope, so it earns
    # its own circuit-specific row and is NOT part of the pooled fallback.
    # monza: deliberately kept below the circuit-credibility bar (well under
    # 300 laps) with a strong POSITIVE true slope, so it's automatically a
    # pooling candidate from the start. Combined with bahrain's rejected
    # (implausible) data, the pooled fit's slope is a weighted average that
    # lands positive -- proving the rejected circuit fit still contributes to
    # a plausible pooled fallback rather than just vanishing, and that an
    # implausible circuit-level result never reaches the output on its own.
    rng = np.random.default_rng(11)
    rows = []
    for circuit, true_coef, n_races, drivers in [
        ("bahrain", -0.05, 20, ["VER", "HAM"]),
        ("imola", 0.08, 20, ["VER", "HAM"]),
        ("monza", 0.6, 4, ["VER", "HAM"]),
    ]:
        for race in range(n_races):
            for driver in drivers:
                for lap in range(1, 21):
                    corrected = 90 + true_coef * lap + 0.001 * lap**2 + rng.normal(0, 0.1)
                    rows.append(
                        {
                            "Compound": "MEDIUM",
                            "CircuitId": circuit,
                            "Driver": driver,
                            "TyreLife": float(lap),
                            "TyreLifeSquared": float(lap**2),
                            "TrackTemp": 30.0,
                            "CorrectedLapTimeSeconds": corrected,
                            "RegulationEra": "2022-2025 ground-effect",
                        }
                    )
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    # bahrain's implausible circuit-level fit must not appear
    assert not ((results["scope"] == "circuit") & (results["circuit_id"] == "bahrain")).any()
    # monza never had enough laps for its own circuit-level fit either
    assert not ((results["scope"] == "circuit") & (results["circuit_id"] == "monza")).any()
    # imola's plausible circuit-level fit should still appear on its own
    imola_row = results[(results["scope"] == "circuit") & (results["circuit_id"] == "imola")]
    assert len(imola_row) == 1
    assert imola_row.iloc[0]["tyre_life_coef"] > 0
    # a pooled fallback should exist, combining bahrain's rejected laps with monza's sparse leftovers
    pooled_rows = results[results["scope"] == "pooled"]
    assert len(pooled_rows) == 1
    assert pooled_rows.iloc[0]["tyre_life_coef"] > 0


def test_fit_degradation_models_stratifies_by_regulation_era():
    rng = np.random.default_rng(13)
    rows = []
    for era in ["2018-2021 aero", "2022-2025 ground-effect"]:
        for race in range(40):
            for driver in ["VER", "HAM", "LEC"]:
                for lap in range(1, 21):
                    corrected = 90 + 0.08 * lap + 0.001 * lap**2 + rng.normal(0, 0.15)
                    rows.append(
                        {
                            "Compound": "MEDIUM",
                            "CircuitId": "bahrain",
                            "Driver": driver,
                            "TyreLife": float(lap),
                            "TyreLifeSquared": float(lap**2),
                            "TrackTemp": 30.0,
                            "CorrectedLapTimeSeconds": corrected,
                            "RegulationEra": era,
                        }
                    )
    frame = pd.DataFrame(rows)

    results = model.fit_degradation_models(frame, min_laps_for_circuit_model=300)

    assert set(results["era"]) == {"2018-2021 aero", "2022-2025 ground-effect"}
    assert len(results[results["circuit_id"] == "bahrain"]) == 2  # one row per era, not pooled across eras
