from __future__ import annotations

from modeling.optimization import degradation_lookup, solver


def per_scenario_costs(
    stint_lengths: list[int],
    cumulative_cost_tables: list[list[int]],
    evaluation_scenarios: list[list[bool]],
    pit_loss_seconds: float,
) -> list[float]:
    # prices any already-chosen set of stint lengths against each scenario in
    # turn -- solver.solve_stint_lengths would instead re-time the pit stops
    # for whatever scenario set it's handed, which defeats the point of
    # asking how a plan committed to in advance holds up against scenarios
    # it wasn't built around
    pit_laps = []
    running_total = stint_lengths[0]
    for stint_length in stint_lengths[1:]:
        pit_laps.append(running_total)
        running_total += stint_length

    stint_cost_seconds = sum(
        cumulative_cost_tables[i][stint_lengths[i]] / degradation_lookup.CENTISECONDS_PER_SECOND
        for i in range(len(stint_lengths))
    )

    costs = []
    for scenario in evaluation_scenarios:
        pit_cost_seconds = 0.0
        for pit_lap in pit_laps:
            is_sc = scenario[pit_lap - 1]
            pit_cost_seconds += pit_loss_seconds * solver.PIT_LOSS_SC_FRACTION if is_sc else pit_loss_seconds
        costs.append(stint_cost_seconds + pit_cost_seconds)

    return costs
