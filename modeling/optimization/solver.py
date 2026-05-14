from __future__ import annotations

from ortools.sat.python import cp_model

MIN_STINT_LENGTH = 3
PIT_LOSS_SC_FRACTION = 0.3
MAX_SOLVE_SECONDS = 10.0


def solve_stint_lengths(
    race_length: int,
    cumulative_cost_tables: list[list[int]],
    scenarios: list[list[bool]],
    pit_loss_seconds: float,
) -> dict:
    n_stints = len(cumulative_cost_tables)
    centiseconds_pit_loss_green = round(pit_loss_seconds * 100)
    centiseconds_pit_loss_sc = round(pit_loss_seconds * 100 * PIT_LOSS_SC_FRACTION)

    model = cp_model.CpModel()
    stint_lengths = [
        model.NewIntVar(MIN_STINT_LENGTH, race_length, f"stint_len_{i}") for i in range(n_stints)
    ]
    model.Add(sum(stint_lengths) == race_length)

    stint_costs = []
    for i, table in enumerate(cumulative_cost_tables):
        cost = model.NewIntVar(0, max(table) + 1, f"stint_cost_{i}")
        model.AddElement(stint_lengths[i], table, cost)
        stint_costs.append(cost)

    pit_laps = []
    running_sum = stint_lengths[0]
    for i in range(1, n_stints):
        pit_lap_var = model.NewIntVar(1, race_length, f"pit_lap_{i}")
        model.Add(pit_lap_var == running_sum)
        pit_laps.append(pit_lap_var)
        running_sum = running_sum + stint_lengths[i]

    scenario_totals = []
    for s, sc_active in enumerate(scenarios):
        padded = [0] + [1 if active else 0 for active in sc_active]
        pit_losses = []
        for j, pit_lap in enumerate(pit_laps):
            is_sc = model.NewBoolVar(f"is_sc_s{s}_p{j}")
            model.AddElement(pit_lap, padded, is_sc)
            pit_loss = model.NewIntVar(
                centiseconds_pit_loss_sc, centiseconds_pit_loss_green, f"pit_loss_s{s}_p{j}"
            )
            model.Add(pit_loss == centiseconds_pit_loss_green).OnlyEnforceIf(is_sc.Not())
            model.Add(pit_loss == centiseconds_pit_loss_sc).OnlyEnforceIf(is_sc)
            pit_losses.append(pit_loss)
        scenario_total = model.NewIntVar(0, 10_000_000, f"scenario_total_{s}")
        model.Add(scenario_total == sum(stint_costs) + sum(pit_losses))
        scenario_totals.append(scenario_total)

    total_cost = model.NewIntVar(0, 10_000_000 * len(scenario_totals), "total_cost")
    model.Add(total_cost == sum(scenario_totals))
    model.Minimize(total_cost)

    cp_solver = cp_model.CpSolver()
    cp_solver.parameters.max_time_in_seconds = MAX_SOLVE_SECONDS
    status = cp_solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible", "stint_lengths": None, "pit_laps": None, "expected_cost_seconds": None}

    return {
        "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
        "stint_lengths": [cp_solver.Value(v) for v in stint_lengths],
        "pit_laps": [cp_solver.Value(v) for v in pit_laps],
        "expected_cost_seconds": cp_solver.Value(total_cost) / 100.0 / len(scenario_totals),
    }
