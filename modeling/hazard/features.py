from __future__ import annotations

import pandas as pd

from modeling.hazard import lap_mapping

PANEL_COLUMNS = [
    "Season",
    "Round",
    "CircuitId",
    "Lap",
    "RaceLength",
    "LapFraction",
    "IsLapOne",
    "IncidentsSoFar",
    "Event",
]


def build_hazard_panel(
    laps: pd.DataFrame, track_status: pd.DataFrame, schedule: pd.DataFrame
) -> pd.DataFrame:
    race_clock = lap_mapping.build_race_clock(laps)
    event_starts = lap_mapping.hazard_event_starts(track_status)
    event_laps = lap_mapping.map_events_to_laps(event_starts, race_clock)
    event_lap_set = set(zip(event_laps["Season"], event_laps["Round"], event_laps["Lap"]))

    race_lengths = race_clock.groupby(["Season", "Round"])["LapNumber"].max()
    circuit_by_race = schedule.set_index(["Season", "Round"])["CircuitId"]

    rows = []
    for (season, round_number), race_length in race_lengths.items():
        if (season, round_number) not in circuit_by_race.index:
            print(f"skip {season} round {round_number}: not in schedule")
            continue
        circuit_id = circuit_by_race.loc[(season, round_number)]
        incidents_so_far = 0
        for lap in range(1, int(race_length) + 1):
            is_event = (season, round_number, lap) in event_lap_set
            rows.append(
                {
                    "Season": season,
                    "Round": round_number,
                    "CircuitId": circuit_id,
                    "Lap": lap,
                    "RaceLength": race_length,
                    "LapFraction": lap / race_length,
                    "IsLapOne": int(lap == 1),
                    "IncidentsSoFar": incidents_so_far,
                    "Event": int(is_event),
                }
            )
            if is_event:
                incidents_so_far += 1

    return pd.DataFrame(rows, columns=PANEL_COLUMNS)


def add_variant(panel: pd.DataFrame, variant_map: pd.Series) -> pd.DataFrame:
    panel = panel.copy()
    keys = list(zip(panel["Season"], panel["Round"], panel["CircuitId"]))
    panel["Variant"] = pd.Series(keys, index=panel.index).map(variant_map)
    return panel
