from __future__ import annotations

import pandas as pd

DRY_COMPOUNDS = {"SOFT", "MEDIUM", "HARD"}


def accurate_laps(laps: pd.DataFrame) -> pd.DataFrame:
    mask = (
        laps["IsAccurate"].astype(bool)
        & laps["LapTime"].notna()
        & laps["TyreLife"].notna()
        & (laps["TyreLife"] >= 1)
    )
    return laps.loc[mask].reset_index(drop=True)


def exclude_rain_affected_dry_compound_laps(frame: pd.DataFrame) -> pd.DataFrame:
    is_dry_compound = frame["Compound"].isin(DRY_COMPOUNDS)
    is_rainy = frame["Rainfall"].astype(bool)
    drop_mask = is_dry_compound & is_rainy
    return frame.loc[~drop_mask].reset_index(drop=True)
