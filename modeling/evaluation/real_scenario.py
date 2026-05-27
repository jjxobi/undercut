from __future__ import annotations

import pandas as pd

from modeling.hazard.lap_mapping import HAZARD_STATUS_CODES


def build_real_scenario(laps: pd.DataFrame, season: int, round_number: int, race_length: int) -> list[bool]:
    race_laps = laps[(laps["Season"] == season) & (laps["Round"] == round_number)]
    is_active = [False] * (race_length + 1)

    for lap_number, group in race_laps.groupby("LapNumber"):
        lap = int(lap_number)
        if lap < 1 or lap > race_length:
            continue
        statuses = group["TrackStatus"].astype(str)
        has_hazard = statuses.apply(
            lambda status: any(code in status for code in HAZARD_STATUS_CODES)
        ).any()
        if has_hazard:
            is_active[lap] = True

    return is_active[1:]
