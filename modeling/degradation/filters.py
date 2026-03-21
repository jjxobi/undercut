from __future__ import annotations

import pandas as pd

WET_COMPOUNDS = {"WET", "INTERMEDIATE"}


def accurate_laps(laps: pd.DataFrame) -> pd.DataFrame:
    mask = (
        laps["IsAccurate"].astype(bool)
        & laps["LapTime"].notna()
        & laps["TyreLife"].notna()
        & (laps["TyreLife"] >= 1)
        & (laps["TrackStatus"] == "1")
        & laps["Time"].notna()
    )
    return laps.loc[mask].reset_index(drop=True)


def exclude_rain_affected_dry_compound_laps(frame: pd.DataFrame) -> pd.DataFrame:
    is_wet_compound = frame["Compound"].isin(WET_COMPOUNDS)
    is_rainy = frame["Rainfall"].astype("boolean").fillna(False).astype(bool)
    drop_mask = (~is_wet_compound) & is_rainy
    return frame.loc[~drop_mask].reset_index(drop=True)
