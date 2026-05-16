import pandas as pd

from modeling.optimization import strategy


def _coefficients() -> pd.DataFrame:
    # HARD degrades slowest, SOFT fastest -- a real degradation model would
    # produce this ordering; verifies optimize_strategy actually compares
    # across sequences rather than just returning the first one.
    rows = []
    for compound, coef in [("SOFT", 0.20), ("MEDIUM", 0.10), ("HARD", 0.05)]:
        rows.append(
            {
                "era": "2018-2021 aero",
                "compound": compound,
                "scope": "pooled",
                "circuit_id": None,
                "tyre_life_coef": coef,
                "tyre_life_squared_coef": 0.0,
            }
        )
    return pd.DataFrame(rows)


def test_optimize_strategy_returns_a_feasible_result():
    result = strategy.optimize_strategy(
        race_length=30,
        circuit_id="bahrain",
        era="2018-2021 aero",
        degradation_coefficients=_coefficients(),
        scenarios=[[False] * 30],
        pit_loss_seconds=24.0,
    )

    assert result["status"] in ("optimal", "feasible")
    assert sum(result["stint_lengths"]) == 30
    assert result["compounds"] in strategy.CANDIDATE_COMPOUND_SEQUENCES


def test_optimize_strategy_tries_multiple_sequences_and_picks_the_cheapest():
    result = strategy.optimize_strategy(
        race_length=30,
        circuit_id="bahrain",
        era="2018-2021 aero",
        degradation_coefficients=_coefficients(),
        scenarios=[[False] * 30],
        pit_loss_seconds=24.0,
        compound_sequences=[["SOFT", "SOFT"], ["HARD", "HARD"]],
    )

    # HARD-HARD degrades far slower than SOFT-SOFT with an identical pit-loss
    # structure, so it must win
    assert result["compounds"] == ["HARD", "HARD"]
