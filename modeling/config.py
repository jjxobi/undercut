from __future__ import annotations

import warnings

LAST_CONFIRMED_SEASON = 2026

SEASONS: list[int] = list(range(2018, LAST_CONFIRMED_SEASON + 1))

REGULATION_ERAS: list[dict] = [
    {"name": "2018-2021 aero", "start_season": 2018, "end_season": 2021},
    {"name": "2022-2025 ground-effect", "start_season": 2022, "end_season": 2025},
    {"name": "2026 active-aero", "start_season": 2026, "end_season": None},
]


def regulation_era(season: int) -> str:
    for era in REGULATION_ERAS:
        end = era["end_season"] if era["end_season"] is not None else season
        if era["start_season"] <= season <= end:
            if era["end_season"] is None and season > LAST_CONFIRMED_SEASON:
                warnings.warn(
                    f"season {season} is beyond the last confirmed regulation era "
                    f"({LAST_CONFIRMED_SEASON}). Treating it as {era['name']} until a new "
                    "era boundary is added to REGULATION_ERAS -- check whether new technical "
                    "regulations actually apply.",
                    stacklevel=2,
                )
            return era["name"]
    raise ValueError(f"no regulation era configured for season {season}")
