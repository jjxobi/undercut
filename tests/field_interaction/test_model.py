import numpy as np
import pandas as pd

from modeling.field_interaction import model


def _synthetic_frame() -> pd.DataFrame:
    # "steady" circuit: PositionDelta always near 0, low variance (like Monaco).
    # "chaotic" circuit: PositionDelta swings widely (like a wet-race circuit).
    # "sparse" circuit: only 3 races -- should get shrunk toward the population value.
    rng = np.random.default_rng(4)
    rows = []
    for circuit_index, (circuit, true_sd, n_races) in enumerate(
        [("steady", 1.0, 60), ("chaotic", 8.0, 60), ("sparse", 8.0, 3)]
    ):
        season = 2000 + circuit_index
        for race in range(n_races):
            for _driver in range(20):
                delta = rng.normal(0, true_sd)
                rows.append(
                    {"CircuitId": circuit, "Season": season, "Round": race, "PositionDelta": delta}
                )
    return pd.DataFrame(rows)


def test_fit_position_volatility_recovers_relative_circuit_ordering():
    frame = _synthetic_frame()

    result = model.fit_position_volatility(frame)

    steady = result[result["circuit_id"] == "steady"].iloc[0]["position_delta_sd"]
    chaotic = result[result["circuit_id"] == "chaotic"].iloc[0]["position_delta_sd"]
    assert steady < chaotic


def test_fit_position_volatility_shrinks_sparse_circuit_toward_population():
    frame = _synthetic_frame()

    result = model.fit_position_volatility(frame)

    population_sd = result[result["circuit_id"].isna()].iloc[0]["position_delta_sd"]
    sparse_raw_sd = frame[frame["CircuitId"] == "sparse"]["PositionDelta"].std()
    sparse_shrunk_sd = result[result["circuit_id"] == "sparse"].iloc[0]["position_delta_sd"]

    # shrunk estimate must sit strictly between the tiny-sample raw estimate and
    # the population value -- proof that shrinkage is actually happening, not
    # just that the number differs from the raw estimate for some other reason
    low, high = sorted([sparse_raw_sd, population_sd])
    assert low < sparse_shrunk_sd < high


def test_fit_position_volatility_produces_one_row_per_circuit_plus_population():
    frame = _synthetic_frame()

    result = model.fit_position_volatility(frame)

    assert set(result["circuit_id"].dropna()) == {"steady", "chaotic", "sparse"}
    assert result["circuit_id"].isna().sum() == 1
