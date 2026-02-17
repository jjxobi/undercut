from __future__ import annotations

SEASONS: list[int] = list(range(2018, 2027))

REGULATION_ERAS: list[dict] = [
    {"name": "2018-2021 aero", "start_season": 2018, "end_season": 2021},
    {"name": "2022-2025 ground-effect", "start_season": 2022, "end_season": 2025},
    {"name": "2026 active-aero", "start_season": 2026, "end_season": None},
]


def regulation_era(season: int) -> str:
    for era in REGULATION_ERAS:
        end = era["end_season"] if era["end_season"] is not None else season
        if era["start_season"] <= season <= end:
            return era["name"]
    raise ValueError(f"no regulation era configured for season {season}")
