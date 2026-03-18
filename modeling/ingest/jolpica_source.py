from __future__ import annotations

import json
import time
from pathlib import Path

import requests

BASE_URL = "https://api.jolpi.ca/ergast/f1"
CACHE_DIR = Path("data/raw/jolpica_cache")

MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 2
MAX_BACKOFF_SECONDS = 30


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _retry_delay_seconds(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return min(INITIAL_BACKOFF_SECONDS * (2**attempt), MAX_BACKOFF_SECONDS)


def _get_json(path: str, cache_key: str, refresh: bool = False) -> dict:
    cache_file = _cache_path(cache_key)
    if cache_file.exists() and not refresh:
        return json.loads(cache_file.read_text())

    url = f"{BASE_URL}/{path}"
    for attempt in range(MAX_RETRIES + 1):
        response = requests.get(url, timeout=30)
        if response.status_code == 429 and attempt < MAX_RETRIES:
            time.sleep(_retry_delay_seconds(response, attempt))
            continue
        response.raise_for_status()
        break

    payload = response.json()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload))
    return payload


def season_schedule(season: int, refresh: bool = False) -> list[dict]:
    payload = _get_json(f"{season}.json", f"schedule_{season}", refresh=refresh)
    return payload["MRData"]["RaceTable"]["Races"]


def race_results(season: int, round_number: int, refresh: bool = False) -> list[dict]:
    key = f"results_{season}_{round_number}"
    payload = _get_json(f"{season}/{round_number}/results.json", key, refresh=refresh)
    races = payload["MRData"]["RaceTable"]["Races"]
    return races[0]["Results"] if races else []
