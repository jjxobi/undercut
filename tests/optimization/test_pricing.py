import pytest

from modeling.optimization import pricing


def test_per_scenario_costs_matches_hand_computation():
    # two one-pit-stop plans over a 10-lap span, pitting after lap 5 (pit_laps
    # derives from stint_lengths, so [5, 5] pits once, after the first stint)
    stint_lengths = [5, 5]
    cumulative_cost_tables = [
        [0, 0, 0, 0, 0, 500],  # first stint: 5 laps cost 500 centiseconds = 5.0s
        [0, 0, 0, 0, 0, 300],  # second stint: 5 laps cost 300 centiseconds = 3.0s
    ]
    pit_loss_seconds = 20.0

    no_sc_scenario = [False] * 10
    sc_scenario = [False] * 10
    sc_scenario[4] = True  # safety car active on lap 5, the pit lap

    costs = pricing.per_scenario_costs(
        stint_lengths, cumulative_cost_tables, [no_sc_scenario, sc_scenario], pit_loss_seconds
    )

    # degradation cost is the same 5.0 + 3.0 = 8.0s either way; the pit lap
    # costs the full 20.0s under green but only 30% of that under a safety car
    assert costs == pytest.approx([8.0 + 20.0, 8.0 + 20.0 * 0.3])
