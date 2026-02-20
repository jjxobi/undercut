from __future__ import annotations

import json
from pathlib import Path

import requests

BASE_URL = "https://api.jolpi.ca/ergast/f1"
CACHE_DIR = Path("data/raw/jolpica_cache")


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _get_json(path: str, cache_key: str) -> dict:
    cache_file = _cache_path(cache_key)
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    response = requests.get(f"{BASE_URL}/{path}", timeout=30)
    response.raise_for_status()
    payload = response.json()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload))
    return payload


def season_schedule(season: int) -> list[dict]:
    payload = _get_json(f"{season}.json", f"schedule_{season}")
    return payload["MRData"]["RaceTable"]["Races"]


def race_results(season: int, round_number: int) -> list[dict]:
    key = f"results_{season}_{round_number}"
    payload = _get_json(f"{season}/{round_number}/results.json", key)
    races = payload["MRData"]["RaceTable"]["Races"]
    return races[0]["Results"] if races else []
