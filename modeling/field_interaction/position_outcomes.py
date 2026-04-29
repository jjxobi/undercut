from __future__ import annotations

import pandas as pd


def build_position_change_frame(results: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    frame = results.merge(
        schedule[["Season", "Round", "CircuitId"]], on=["Season", "Round"], how="inner"
    )

    # GridPosition == 0 is the Ergast/Jolpica sentinel for a pit-lane start, not a
    # real grid slot. Treating it as position 0 manufactures large fake position
    # gains for pit-lane starters -- exclude rows without a genuine grid slot.
    frame = frame[frame["GridPosition"] > 0]

    # Only classified finishers (including lapped cars, e.g. "+1 Lap") represent a
    # genuine racing outcome. Retirements/DNS/DSQ are attrition, not overtaking --
    # including them conflates reliability with overtaking difficulty and produces
    # misleading circuit rankings (verified against real data: Baku looks like one
    # of the hardest circuits to predict position at when DNFs are included, purely
    # from a high retirement rate in the sampled races, and one of the easiest once
    # they're excluded -- the latter matches an independent grid-vs-finish
    # rank-correlation check far better).
    is_classified = frame["Status"].eq("Finished") | frame["Status"].str.contains("Lap", na=False)
    frame = frame[is_classified]

    frame = frame.dropna(subset=["GridPosition", "Position", "CircuitId"]).copy()
    frame["PositionDelta"] = frame["GridPosition"] - frame["Position"]
    return frame
