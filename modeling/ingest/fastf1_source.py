from __future__ import annotations

from pathlib import Path

import fastf1
import pandas as pd

CACHE_DIR = Path("data/raw/fastf1_cache")


def enable_cache(cache_dir: Path = CACHE_DIR) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))


def load_race_session(season: int, round_number: int):
    session = fastf1.get_session(season, round_number, "R")
    session.load(laps=True, weather=True, telemetry=False, messages=False)
    return session


def laps_frame(session, season: int, round_number: int) -> pd.DataFrame:
    laps = session.laps.copy()
    laps.insert(0, "Season", season)
    laps.insert(1, "Round", round_number)
    return laps


def track_status_frame(session, season: int, round_number: int) -> pd.DataFrame:
    status = session.track_status.copy()
    status.insert(0, "Season", season)
    status.insert(1, "Round", round_number)
    return status


def weather_frame(session, season: int, round_number: int) -> pd.DataFrame:
    weather = session.weather_data.copy()
    weather.insert(0, "Season", season)
    weather.insert(1, "Round", round_number)
    return weather


def stints_frame(laps: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        laps.groupby(["Season", "Round", "Driver", "Stint"])
        .agg(
            Compound=("Compound", "first"),
            StartLap=("LapNumber", "min"),
            EndLap=("LapNumber", "max"),
        )
        .reset_index()
    )
    grouped["StintLength"] = grouped["EndLap"] - grouped["StartLap"] + 1
    return grouped


def pit_stops_frame(laps: pd.DataFrame) -> pd.DataFrame:
    stops = laps.loc[
        laps["PitInTime"].notna(),
        ["Season", "Round", "Driver", "LapNumber", "Stint", "PitInTime", "PitOutTime"],
    ].copy()
    return stops.reset_index(drop=True)
