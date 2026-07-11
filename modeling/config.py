from __future__ import annotations

LAST_CONFIRMED_SEASON = 2026

SEASONS: list[int] = list(range(2018, LAST_CONFIRMED_SEASON + 1))

REGULATION_ERAS: list[dict] = [
    {"name": "2018-2021 aero", "start_season": 2018, "end_season": 2021},
    {"name": "2022-2025 ground-effect", "start_season": 2022, "end_season": 2025},
    {"name": "2026 active-aero", "start_season": 2026, "end_season": LAST_CONFIRMED_SEASON},
]


def regulation_era(season: int) -> str:
    if season > LAST_CONFIRMED_SEASON:
        raise ValueError(
            f"season {season} is beyond the last confirmed regulation era "
            f"({LAST_CONFIRMED_SEASON}). Check whether new technical regulations apply, "
            "add an era boundary to REGULATION_ERAS, then extend LAST_CONFIRMED_SEASON."
        )
    for era in REGULATION_ERAS:
        if era["start_season"] <= season <= era["end_season"]:
            return era["name"]
    raise ValueError(f"no regulation era configured for season {season}")
