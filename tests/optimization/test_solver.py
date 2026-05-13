from modeling.optimization import solver


def _linear_table(race_length: int, cost_per_lap_of_age: float) -> list[int]:
    # cumulative cost of n laps at a fixed marginal degradation rate per lap of tyre age
    table = [0]
    total = 0.0
    for n in range(1, race_length + 1):
        total += cost_per_lap_of_age * (n - 1)
        table.append(round(total * 100))
    return table


def test_solve_stint_lengths_two_stints_sums_to_race_length():
    race_length = 20
    tables = [_linear_table(race_length, 0.10), _linear_table(race_length, 0.08)]
    scenarios = [[False] * race_length]

    result = solver.solve_stint_lengths(race_length, tables, scenarios, pit_loss_seconds=24.0)

    assert result["status"] == "optimal"
    assert sum(result["stint_lengths"]) == race_length
    assert len(result["stint_lengths"]) == 2
    assert len(result["pit_laps"]) == 1
    assert result["pit_laps"][0] == result["stint_lengths"][0]


def test_solve_stint_lengths_three_stints_produces_two_pit_laps():
    race_length = 30
    tables = [_linear_table(race_length, 0.10), _linear_table(race_length, 0.09), _linear_table(race_length, 0.08)]
    scenarios = [[False] * race_length, [False] * 14 + [True] * 3 + [False] * 13]

    result = solver.solve_stint_lengths(race_length, tables, scenarios, pit_loss_seconds=24.0)

    assert result["status"] == "optimal"
    assert sum(result["stint_lengths"]) == race_length
    assert len(result["pit_laps"]) == 2
    assert result["pit_laps"][0] < result["pit_laps"][1]


def test_solve_stint_lengths_prefers_pitting_during_a_safety_car():
    # a safety car active on laps 10-12 should pull the single pit stop of a
    # 2-stint strategy toward that window, since pitting there is much cheaper
    race_length = 20
    tables = [_linear_table(race_length, 0.05), _linear_table(race_length, 0.05)]  # symmetric, no other pressure
    scenarios = [[False] * 9 + [True] * 3 + [False] * 8]

    result = solver.solve_stint_lengths(race_length, tables, scenarios, pit_loss_seconds=24.0)

    assert 10 <= result["pit_laps"][0] <= 12


def test_solve_stint_lengths_respects_minimum_stint_length():
    race_length = 10
    tables = [_linear_table(race_length, 0.05), _linear_table(race_length, 0.05), _linear_table(race_length, 0.05)]
    scenarios = [[False] * race_length]

    result = solver.solve_stint_lengths(race_length, tables, scenarios, pit_loss_seconds=24.0)

    assert all(length >= solver.MIN_STINT_LENGTH for length in result["stint_lengths"])
